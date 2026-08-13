#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import PositionTarget, State
from mavros_msgs.srv import CommandBool, CommandTOL, SetMode
from std_msgs.msg import String

from autonomy_benchmark.trajectory import GENERATORS


class TrajCommander(Node):
    def __init__(self):
        super().__init__("traj_commander")
        self.declare_parameter("traj", "circle")
        self.declare_parameter("speed", 2.0)
        self.declare_parameter("size", 5.0)
        self.declare_parameter("z", 5.0)
        self.declare_parameter("duration", 60.0)
        self.declare_parameter("rate", 20.0)
        self.declare_parameter("settle_time", 5.0)

        name = self.get_parameter("traj").value
        self.speed = self.get_parameter("speed").value
        self.size = self.get_parameter("size").value
        self.z = self.get_parameter("z").value
        self.duration = self.get_parameter("duration").value
        self.settle_time = self.get_parameter("settle_time").value
        self.gen = GENERATORS[name]

        self.state = None
        self.pose = None
        self.origin = None
        self.phase = "wait"
        self.phase_t0 = None
        self.traj_t0 = None
        self.pending = None

        self.create_subscription(State, "/mavros/state", self.on_state, 10)
        self.create_subscription(
            PoseStamped,
            "/mavros/local_position/pose",
            self.on_pose,
            qos_profile_sensor_data,
        )
        self.sp_pub = self.create_publisher(
            PositionTarget,
            "/mavros/setpoint_raw/local",
            10,
        )
        self.ref_pub = self.create_publisher(PoseStamped, "/benchmark/reference", 10)
        self.phase_pub = self.create_publisher(String, "/benchmark/phase", 10)

        self.mode_cli = self.create_client(SetMode, "/mavros/set_mode")
        self.arm_cli = self.create_client(CommandBool, "/mavros/cmd/arming")
        self.takeoff_cli = self.create_client(CommandTOL, "/mavros/cmd/takeoff")

        rate = self.get_parameter("rate").value
        self.timer = self.create_timer(1.0 / rate, self.tick)

    def on_state(self, msg):
        self.state = msg

    def on_pose(self, msg):
        self.pose = msg

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def call(self, client, req):
        if self.pending is not None:
            if not self.pending.done():
                return None
            result = self.pending.result()
            self.pending = None
            return result
        if client.service_is_ready():
            self.pending = client.call_async(req)
        return None

    def publish_setpoint(self, pos, vel, acc=(0.0, 0.0, 0.0)):
        sp = PositionTarget()
        sp.header.stamp = self.get_clock().now().to_msg()
        sp.coordinate_frame = PositionTarget.FRAME_LOCAL_NED
        sp.type_mask = (
            PositionTarget.IGNORE_YAW
            | PositionTarget.IGNORE_YAW_RATE
        )
        sp.position.x = self.origin[0] + pos[0]
        sp.position.y = self.origin[1] + pos[1]
        sp.position.z = pos[2]
        sp.velocity.x = vel[0]
        sp.velocity.y = vel[1]
        sp.velocity.z = vel[2]
        sp.acceleration_or_force.x = acc[0]
        sp.acceleration_or_force.y = acc[1]
        sp.acceleration_or_force.z = acc[2]
        self.sp_pub.publish(sp)

        ref = PoseStamped()
        ref.header.stamp = sp.header.stamp
        ref.header.frame_id = "map"
        ref.pose.position.x = sp.position.x
        ref.pose.position.y = sp.position.y
        ref.pose.position.z = sp.position.z
        self.ref_pub.publish(ref)

    def set_phase(self, phase):
        self.phase = phase
        self.pending = None

    def tick(self):
        self.phase_pub.publish(String(data=self.phase))
        if self.phase == "wait":
            if self.state and self.state.connected and self.pose:
                self.set_phase("mode")
        elif self.phase == "mode":
            if self.state.mode != "GUIDED":
                self.call(self.mode_cli, SetMode.Request(custom_mode="GUIDED"))
            else:
                self.set_phase("arm")
        elif self.phase == "arm":
            if not self.state.armed:
                self.call(self.arm_cli, CommandBool.Request(value=True))
            else:
                self.set_phase("takeoff")
        elif self.phase == "takeoff":
            result = self.call(
                self.takeoff_cli, CommandTOL.Request(altitude=float(self.z))
            )
            if result is not None and result.success:
                self.set_phase("climb")
        elif self.phase == "climb":
            if self.pose.pose.position.z > self.z * 0.95:
                self.origin = (self.pose.pose.position.x, self.pose.pose.position.y)
                self.set_phase("settle")
                self.phase_t0 = self.now()
                self.get_logger().info(f"origin: {self.origin}")
        elif self.phase == "settle":
            self.publish_setpoint((0.0, 0.0, self.z), (0.0, 0.0, 0.0))
            if self.now() - self.phase_t0 > self.settle_time:
                self.set_phase("track")
                self.traj_t0 = self.now()
                self.get_logger().info("tracking start")
        elif self.phase == "track":
            t = self.now() - self.traj_t0
            if t > self.duration:
                self.set_phase("hold")
                self.phase_t0 = self.now()
                self.get_logger().info("tracking done")
                return
            pos, vel, acc = self.gen(t, self.speed, self.size, self.z)
            self.publish_setpoint(pos, vel, acc)
        elif self.phase == "hold":
            self.publish_setpoint((0.0, 0.0, self.z), (0.0, 0.0, 0.0))
            if self.now() - self.phase_t0 > 3.0:
                if self.state.mode != "LAND":
                    self.call(self.mode_cli, SetMode.Request(custom_mode="LAND"))
                else:
                    self.set_phase("done")
                    self.get_logger().info("landing")
        elif self.phase == "done":
            if self.state and not self.state.armed:
                self.get_logger().info("benchmark finished")
                raise SystemExit


def main():
    rclpy.init()
    node = TrajCommander()
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    rclpy.shutdown()


if __name__ == "__main__":
    main()
