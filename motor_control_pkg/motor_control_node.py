import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Int32, Bool
from my_robot_interfaces.msg import BesturingsData
import can
import struct
from geometry_msgs.msg import Twist


class MotorControlNode(Node):
    def __init__(self):
        super().__init__('motor_control_node')

        self.bus = can.Bus(interface='socketcan', channel='can0', bitrate=500000)         

        # Subscribers voor de BesturingsData message
        self.BesturingsData_subscription = self.create_subscription(BesturingsData, 'besturings_data', self.motor_control_callback, 10)

        # subscriber voor navigatie stuurcommando
        self.twist_subscription = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)

        self.throttle = 0
        self.steering = 0
        self.direction = 0
        self.brake = 0

        self.timer = self.create_timer(0.04, self.send_can_messages)

    def motor_control_callback(self, msg: BesturingsData):
        self.throttle = int(msg.throttle * 100)  # Scale throttle
        self.brake = int(msg.brake * 100)  # Scale brake
        self.steering = msg.steering
        self.direction = msg.direction
        

    def cmd_vel_callback(self, msg: Twist):
        # functie voor het omzetten van /cmd_vel naar data die geschikt is voor de motor

        # Maximale snelheid en stuurhoek
        max_speed = 2.78  # Maximale snelheid in m/s (10km/h)
        max_steering_angle = 45.0  # Maximale stuurhoek in graden

        # Controleer de richting en pas throttle aan
        if msg.linear.x < 0:
            self.direction = 2  # Achteruit
            linear_speed = abs(msg.linear.x)  # Maak snelheid positief
        else:
            self.direction = 1  # Vooruit
            linear_speed = msg.linear.x

        # Zet lineaire snelheid om naar throttle (0-100)
        self.throttle = int(max(0.0, min(100.0, (linear_speed / max_speed) * 100.0)))

        # Zet hoeksnelheid om naar stuurhoek (-1 tot 1)
        steering_angle_deg = msg.angular.z / max_speed * max_steering_angle
        steering_angle_deg = max(-max_steering_angle, min(max_steering_angle, steering_angle_deg))  # Begrens tot ±45 graden
        self.steering = steering_angle_deg / max_steering_angle  # Normaliseer naar -1 tot 1

        print(f"Throttle: {self.throttle}, Steering: {self.steering}, Direction {self.direction}")


    def send_can_messages(self):
        # uncomment brake message bij echt karte
        
        # brk_msg = can.Message(arbitration_id=0x110, data=[self.brake, 0, 0, 0, 0, 0, 0, 0], is_extended_id=False)
        steering_msg = can.Message(arbitration_id=0x220, data=list(bytearray(struct.pack("f", self.steering))) + [0, 0, 0, 0], is_extended_id=False)
        acc_msg = can.Message(arbitration_id=0x330, data=[self.throttle, 0, self.direction, 0, 0, 0, 0, 0], is_extended_id=False)
        
        # self.bus.send(brk_msg)
        self.bus.send(steering_msg)
        self.bus.send(acc_msg)
        

def main(args=None):
    rclpy.init(args=args)
    node = MotorControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
