# teleop_keyboard/teleop_keyboard/teleop_keyboard_node.py

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from pynput import keyboard
import threading

class TeleopKeyboardNode(Node):
    """
    Нода для управления роботом с клавиатуры.
    Публикует сообщения Twist в топик /cmd_vel только при изменении состояния.
    """
    def __init__(self):
        super().__init__('teleop_keyboard_node')

        # Объявление параметров для скорости
        self.declare_parameter('linear_speed', 0.5)  # м/с
        self.declare_parameter('angular_speed', 1.0) # рад/с

        # Получение значений параметров
        self.linear_speed = self.get_parameter('linear_speed').get_parameter_value().double_value
        self.angular_speed = self.get_parameter('angular_speed').get_parameter_value().double_value
        
        # Создание паблишера
        self.publisher_ = self.create_publisher(Twist, 'cmd_vel', 10)

        # Переменные для хранения текущего состояния скоростей
        self.target_linear_vel = 0.0
        self.target_angular_vel = 0.0
        
        # Переменные для отслеживания нажатых клавиш
        self.pressed_keys = set()
        
        # Последнее опубликованное сообщение, чтобы избежать спама
        self.last_published_twist = Twist()

        self.print_instructions()
        
        # Запускаем слушатель клавиатуры в отдельном потоке
        self.key_listener_thread = threading.Thread(target=self.start_keyboard_listener)
        self.key_listener_thread.daemon = True
        self.key_listener_thread.start()
        
        # Создаем таймер для периодической публикации команд
        # Это гарантирует, что команда будет отправлена, даже если нет новых событий клавиатуры
        # но состояние изменилось.
        self.timer = self.create_timer(0.1, self.publish_twist_if_changed)

    def print_instructions(self):
        """Выводит инструкцию по управлению."""
        self.get_logger().info("---------------------------")
        self.get_logger().info("Управление роботом с помощью WASD:")
        self.get_logger().info("   W: Движение вперед")
        self.get_logger().info("   S: Движение назад")
        self.get_logger().info("   A: Поворот влево")
        self.get_logger().info("   D: Поворот вправо")
        self.get_logger().info("---------------------------")
        self.get_logger().info(f"Линейная скорость: {self.linear_speed} м/с")
        self.get_logger().info(f"Угловая скорость: {self.angular_speed} рад/с")
        self.get_logger().info("---------------------------")
        self.get_logger().info("Нажмите Ctrl+C для выхода.")

    def on_press(self, key):
        """Обработчик нажатия клавиши."""
        try:
            char_key = key.char
            if char_key not in self.pressed_keys:
                self.pressed_keys.add(char_key)
                self.update_target_velocities()
        except AttributeError:
            # Игнорируем специальные клавиши (Shift, Ctrl и т.д.)
            pass

    def on_release(self, key):
        """Обработчик отпускания клавиши."""
        try:
            char_key = key.char
            if char_key in self.pressed_keys:
                self.pressed_keys.remove(char_key)
                self.update_target_velocities()
        except AttributeError:
            pass
        # Если нажата клавиша Esc, можно добавить логику выхода, но Ctrl+C надежнее
        if key == keyboard.Key.esc:
            # Можно реализовать остановку, но лучше завершать через rclpy
            pass

    def update_target_velocities(self):
        """Обновляет целевые скорости на основе нажатых клавиш."""
        self.target_linear_vel = 0.0
        self.target_angular_vel = 0.0

        if 'w' in self.pressed_keys:
            self.target_linear_vel = self.linear_speed
        if 's' in self.pressed_keys:
            self.target_linear_vel = -self.linear_speed
        if 'a' in self.pressed_keys:
            self.target_angular_vel = self.angular_speed
        if 'd' in self.pressed_keys:
            self.target_angular_vel = -self.angular_speed

    def publish_twist_if_changed(self):
        """
        Создает и публикует сообщение Twist, только если оно отличается
        от последнего опубликованного.
        """
        twist = Twist()
        twist.linear.x = self.target_linear_vel
        twist.angular.z = self.target_angular_vel

        # ВАЖНО: Сравниваем текущую команду с последней отправленной
        if (twist.linear.x != self.last_published_twist.linear.x or
            twist.angular.z != self.last_published_twist.angular.z):
            
            self.publisher_.publish(twist)
            self.last_published_twist = twist
            # Логируем только при отправке новой команды
            self.get_logger().info(f'Publishing: Linear x: {twist.linear.x:.2f}, Angular z: {twist.angular.z:.2f}')

    def start_keyboard_listener(self):
        """Запускает слушатель pynput."""
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()
            
    def destroy_node(self):
        # Отправляем команду остановки при выключении ноды
        self.get_logger().info("Отправка команды остановки...")
        stop_twist = Twist()
        self.publisher_.publish(stop_twist)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = TeleopKeyboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Завершение работы по Ctrl+C")
    finally:
        # Уничтожаем ноду, чтобы отправить последнюю команду остановки
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
