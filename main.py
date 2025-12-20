import sys
import argparse
import os

from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QSystemTrayIcon, QMenu
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon, QAction
from qfluentwidgets import (
    FluentIcon,
    MessageBoxBase,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    Theme,
    TitleLabel,
    setTheme,
)


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller/Nuitka"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Nuitka or development
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


class ShutdownMessageBox(MessageBoxBase):
    """基于 MessageBoxBase 的关机提示框"""

    def __init__(self, parent, args) -> None:
        super().__init__(parent)
        self.args = args
        self.remaining = args.countdown if args.countdown else 60

        self._setup_content()
        self._setup_buttons()

    def _setup_content(self) -> None:
        title = TitleLabel("即将关机", self)
        self.subtitle_label = SubtitleLabel(
            f"计算机将在 {self.remaining} 秒后自动关闭。请及时保存您的工作或选择其他操作。", self
        )

        self.viewLayout.addWidget(title)
        self.viewLayout.addWidget(self.subtitle_label)

    def _setup_buttons(self) -> None:
        # 隐藏默认按钮
        self.yesButton.hide()
        self.cancelButton.hide()

        # 创建自定义按钮
        self.primary_btn = PrimaryPushButton(FluentIcon.CHECKBOX, "已阅", self)
        self.secondary_btn = PushButton(FluentIcon.POWER_BUTTON, "立即关机", self)
        self.third_btn = PushButton(FluentIcon.DATE_TIME, f"延迟 {self.args.delay} 分钟", self)
        self.close_btn = PushButton(FluentIcon.CLOSE, "取消关机计划", self)

        self.buttonLayout.addWidget(self.primary_btn)
        self.buttonLayout.addStretch(1)
        self.buttonLayout.addWidget(self.secondary_btn)
        self.buttonLayout.addWidget(self.third_btn)
        self.buttonLayout.addWidget(self.close_btn)

    def update_subtitle(self) -> None:
        self.subtitle_label.setText(
            f"计算机将在 {self.remaining} 秒后自动关闭。请及时保存您的工作或选择其他操作。"
        )


class MainWindow(QWidget):
    """全屏透明主窗口"""

    def __init__(self, args) -> None:
        super().__init__()
        self.args = args
        setTheme(Theme.AUTO)
        self.icon_path = get_resource_path("icon.png")

        # 设置全屏透明窗口
        self.setWindowTitle("Waity")
        self.setWindowIcon(QIcon(self.icon_path))
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showFullScreen()

        # 初始化倒计时
        if self.args.countdown:
            self.remaining = self.args.countdown
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_countdown)
            self.timer.start(1000)

        self._init_ui()
        self._init_tray()

    def _init_ui(self) -> None:
        # 创建消息框
        self.message_box = ShutdownMessageBox(self, self.args)
        self.message_box.remaining = self.remaining

        # 连接按钮信号
        self.message_box.primary_btn.clicked.connect(self.on_primary_clicked)
        self.message_box.secondary_btn.clicked.connect(self.on_secondary_clicked)
        self.message_box.third_btn.clicked.connect(self.on_third_clicked)
        self.message_box.close_btn.clicked.connect(self.cancel_shutdown)

        # 显示消息框
        self.message_box.show()

    def _init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.icon_path))
        self.tray_icon.setToolTip(f"Waity：{self.remaining} 秒后自动关机")

        # 创建托盘菜单
        tray_menu = QMenu()

        self.time_action = QAction(f"剩余时间：{self.remaining} 秒", self)
        tray_menu.addAction(self.time_action)

        delay_action = QAction(f"延迟 {self.args.delay} 分钟", self)
        delay_action.triggered.connect(self.on_third_clicked)
        tray_menu.addAction(delay_action)

        cancel_action = QAction("取消关机计划", self)
        cancel_action.triggered.connect(self.cancel_shutdown)
        tray_menu.addAction(cancel_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showFullScreen()
            self.message_box.show()
            self.raise_()
            self.activateWindow()

    def update_ui(self):
        self.message_box.remaining = self.remaining
        self.message_box.update_subtitle()
        self.time_action.setText(f"剩余时间：{self.remaining} 秒")
        self.tray_icon.setToolTip(f"Waity：{self.remaining} 秒后自动关机")

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def update_countdown(self):
        self.remaining -= 1
        if self.remaining > 0:
            self.update_ui()
        else:
            self.timer.stop()
            # 执行关机
            self.perform_shutdown()

    def perform_shutdown(self):
        # 这里添加关机命令
        import os
        os.system("shutdown /s /t 0")

    def cancel_shutdown(self):
        self.message_box.close()
        # 延迟关闭窗口，让 MessageBox 动画播放完成
        QTimer.singleShot(500, self.quit_app)

    def quit_app(self):
        if hasattr(self, 'timer'):
            self.timer.stop()
        QApplication.quit()

    def on_primary_clicked(self):
        self.message_box.hide()
        self.hide()

    def on_secondary_clicked(self):
        self.perform_shutdown()

    def on_third_clicked(self):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.remaining += self.args.delay * 60
            self.update_ui()
        else:
            self.remaining = self.args.delay * 60
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_countdown)
            self.timer.start(1000)
            self.update_ui()
        self.message_box.close()
        # 延迟关闭窗口，让 MessageBox 动画播放完成
        QTimer.singleShot(300, self.hide)


def main() -> None:
    parser = argparse.ArgumentParser(description='Waity')
    parser.add_argument('--countdown', type=int, default=60, help='倒计时时长（秒），默认 60 秒')
    parser.add_argument('--delay', type=int, default=3, help='延迟选项时长（分钟），默认 3 分钟')
    args = parser.parse_args()

    if args.countdown <= 0 or args.delay <= 0:
        print("错误：--countdown 和 --delay 必须是非零自然数")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = MainWindow(args)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
