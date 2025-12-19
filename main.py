import sys
import argparse
import os

from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout, QLabel, QSystemTrayIcon, QMenu
from PySide6.QtCore import QTimer, Qt, QEvent
from PySide6.QtGui import QIcon, QAction
from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
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


class MainDialog(QDialog):
    def __init__(self, args) -> None:
        super().__init__()
        self.args = args
        setTheme(Theme.AUTO)
        self.icon_path = get_resource_path("icon.png")
        self.setWindowTitle("Waity")
        self.setWindowIcon(QIcon(self.icon_path))
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.resize(460, 260)
        if self.args.countdown:
            self.remaining = self.args.countdown
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_countdown)
            self.timer.start(1000)
        self._init_ui()
        self._init_tray()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 16)

        title = TitleLabel("即将关机")
        layout.addWidget(title)

        subtitle = SubtitleLabel("计算机将在 60 秒后自动关闭。请及时保存您的工作或选择其他操作。")
        layout.addWidget(subtitle)

        if self.args.countdown:
            self.subtitle_label = SubtitleLabel(f"计算机将在 {self.remaining} 秒后自动关闭。请及时保存您的工作或选择其他操作。")
            layout.addWidget(self.subtitle_label)
            # 隐藏原来的subtitle
            subtitle.hide()
        else:
            self.subtitle_label = subtitle

        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)
        layout.addLayout(button_row)

        self.primary_btn = PrimaryPushButton(FluentIcon.CHECKBOX, "已阅")
        self.secondary_btn = PushButton(FluentIcon.POWER_BUTTON, "立即关机")
        self.third_btn = PushButton(FluentIcon.DATE_TIME, f"延迟 {self.args.delay} 分钟")
        self.close_btn = PushButton(FluentIcon.CLOSE, "取消关机计划")

        button_row.addWidget(self.primary_btn)
        button_row.addStretch(1)
        button_row.addWidget(self.secondary_btn)
        button_row.addWidget(self.third_btn)
        button_row.addWidget(self.close_btn)

        self.primary_btn.clicked.connect(self.on_primary_clicked)
        self.secondary_btn.clicked.connect(self.on_secondary_clicked)
        self.third_btn.clicked.connect(self.on_third_clicked)
        self.close_btn.clicked.connect(self.cancel_shutdown)

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
            self.show()
            self.raise_()
            self.activateWindow()

    def update_ui(self):
        self.subtitle_label.setText(f"计算机将在 {self.remaining} 秒后自动关闭。请及时保存您的工作或选择其他操作。")
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
        self.quit_app()

    def quit_app(self):
        if hasattr(self, 'timer'):
            self.timer.stop()
        QApplication.quit()

    def on_primary_clicked(self):
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
        self.hide()


def main() -> None:
    parser = argparse.ArgumentParser(description='Waity')
    parser.add_argument('--countdown', type=int, default=60, help='倒计时时长（秒），默认 60 秒')
    parser.add_argument('--delay', type=int, default=3, help='延迟选项时长（分钟），默认 3 分钟')
    args = parser.parse_args()

    if args.countdown <= 0 or args.delay <= 0:
        print("错误：--countdown 和 --delay 必须是非零自然数")
        sys.exit(1)

    app = QApplication(sys.argv)
    dialog = MainDialog(args)
    dialog.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
