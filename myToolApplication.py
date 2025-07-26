import markdown
import sys
import os
import time
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QTextEdit, QPushButton, QLabel, QPlainTextEdit, QFormLayout, QLineEdit, 
    QStackedWidget, QSizePolicy, QSpacerItem, QComboBox, QMessageBox,
    QFrame, QSplitter, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QStyledItemDelegate, QProxyStyle, QStyle
)
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QPalette, QBrush, QIcon

# 导入新的后端控制器
from applicationController import app_controller

from config import APP_NAME, UI_FONTS, LOGS_DIR, LOG_FILENAME_PREFIX, LOG_FILENAME_FORMAT, API_URL_VALID_PREFIXES


class BackendInitializationThread(QThread):
    """用于在后台初始化控制器的线程"""
    initialization_done = pyqtSignal(bool, str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def run(self):
        try:
            self.controller.initialize_app()
            self.initialization_done.emit(True, "Backend initialized successfully.")
        except Exception as e:
            self.initialization_done.emit(False, f"Backend initialization failed: {e}")


def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容 PyInstaller 打包和源码运行"""
    try:
        # 如果是PyInstaller打包后的环境
        if hasattr(sys, '_MEIPASS'):
            meipass_path = os.path.join(getattr(sys, '_MEIPASS'), relative_path)
            if os.path.exists(meipass_path):
                return meipass_path
        
        # 尝试从当前工作目录读取
        current_dir_path = os.path.join(os.getcwd(), relative_path)
        if os.path.exists(current_dir_path):
            return current_dir_path
        
        # 尝试从exe所在目录读取
        if hasattr(sys, 'executable'):
            exe_dir = os.path.dirname(sys.executable)
            exe_dir_path = os.path.join(exe_dir, relative_path)
            if os.path.exists(exe_dir_path):
                return exe_dir_path
        
        # 尝试从源码目录读取
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_dir_path = os.path.join(script_dir, relative_path)
        if os.path.exists(script_dir_path):
            return script_dir_path
        
        return current_dir_path
        
    except Exception as e:
        print(f"resource_path error for {relative_path}: {e}")
        return relative_path

class LogWidget(QTextEdit):
    """日志组件"""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont('Consolas', 10))
        # 设置浅色背景、深色字体
        pal = self.palette()
        pal.setColor(QPalette.Base, QColor(245, 245, 245))
        pal.setColor(QPalette.Text, QColor(30, 30, 30))
        self.setPalette(pal)
        self.setFixedHeight(200)
        
        # 创建日志文件
        self.log_filename = self.create_log_file()
        self.log_buffer = []
        self.last_write_time = time.time()
        
        # 创建定时器，每10秒写入日志文件
        self.timer = QTimer()
        self.timer.timeout.connect(self.flush_log_buffer)
        self.timer.start(10000)  # 10秒
    
    def create_log_file(self):
        """创建日志文件"""
        if not os.path.exists(LOGS_DIR):
            os.makedirs(LOGS_DIR)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(LOGS_DIR, LOG_FILENAME_FORMAT.format(prefix=LOG_FILENAME_PREFIX, timestamp=timestamp))
        return filename
    
    def append_log(self, msg):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        
        self.append(log_msg)
        self.log_buffer.append(log_msg)
        
        # 滚动到底部
        sb = self.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())
    
    def flush_log_buffer(self):
        """将日志缓冲区写入文件"""
        if self.log_buffer:
            try:
                with open(self.log_filename, "a", encoding="utf-8") as f:
                    for msg in self.log_buffer:
                        f.write(msg + "\n")
                self.log_buffer.clear()
                self.last_write_time = time.time()
            except Exception as e:
                print(f"写入日志文件失败: {e}")
    
    def closeEvent(self, event):
        """关闭时写入日志"""
        self.flush_log_buffer()
        super().closeEvent(event)

class StyledSidebar(QListWidget):
    """样式化的侧边栏"""
    def __init__(self, items, width=200):
        super().__init__()
        self.setFixedWidth(width)
        self.setSpacing(8)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet('''
            QListView, QListWidget {
                outline: none;
            }
            QListWidget {
                border: none;
                background: transparent;
            }
            QListWidget::item {
                background: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                margin: 4px 0;
                padding: 12px 16px;
                font-size: 14px;
                color: #333;
                font-weight: 500;
            }
            QListWidget::item:hover {
                background: #e0e0e0;
                border-color: #b0b0b0;
            }
            QListWidget::item:selected {
                background: #0078d4;
                color: white;
                border-color: #0078d4;
            }
        ''')
        
        # 添加项目
        for item_text in items:
            self.addItem(item_text)
        
        # 默认选择第一个项目
        if self.count() > 0:
            self.setCurrentRow(0)

class NoFocusRectStyle(QProxyStyle):
    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)

class EditModeDelegate(QStyledItemDelegate):
    def __init__(self, parent, is_editing_func):
        super().__init__(parent)
        self.is_editing_func = is_editing_func
    def paint(self, painter, option, index):
        if self.is_editing_func() and bool(index.flags() & Qt.ItemFlag.ItemIsEditable):
            painter.save()
            painter.fillRect(option.rect, QColor('#fffbe6'))
            painter.restore()
        super().paint(painter, option, index)

class ConfigTableWidget(QTableWidget):
    """配置表格组件"""
    header_key_map = {
        "ID": "id",
        "IP地址": "ip",
        "端口": "port",
        "用户名": "username",
        "密码": "password",
        "私钥": "privateKey",
        "地址": "address"
    }
    def __init__(self, headers, data=None):
        super().__init__()
        self.headers = headers
        self._editing = False
        self.setItemDelegate(EditModeDelegate(self, lambda: self._editing))
        self.setStyle(NoFocusRectStyle(self.style()))
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        # 设置表格样式
        self.setStyleSheet('''
            QTableWidget {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 12px;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
                border-radius: 8px;
                background: transparent;
            }
            QTableWidget::item:selected {
                background: transparent;
                border: 2px solid orange;
                color: #333;
            }
            QTableWidget::item:focus {
                outline: none;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #d0d0d0;
                font-weight: bold;
                font-size: 15px;
            }
        ''')
        # 设置列宽：ID列固定，其余均分
        for i, h in enumerate(headers):
            if h == "ID":
                self.setColumnWidth(i, 60)
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)
            else:
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        self.horizontalHeader().setStretchLastSection(True)
        if data:
            self.load_data(data)
    
    def load_data(self, data):
        """加载数据"""
        print(f"ConfigTableWidget.load_data: 加载 {len(data)} 条数据")
        self.setRowCount(len(data))
        for row, item in enumerate(data):
            print(f"  行{row}: {item}")
            for col, header in enumerate(self.headers):
                key = self.header_key_map.get(header, header)
                if key in item:
                    value = str(item[key])
                    table_item = QTableWidgetItem(value)
                    table_item.setFlags(Qt.ItemFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable))
                    self.setItem(row, col, table_item)
                    print(f"    列{col}({header}): {value}")
                else:
                    print(f"    列{col}({header}): 未找到")
        print(f"表格行数: {self.rowCount()}, 列数: {self.columnCount()}")
    
    def get_data(self):
        """获取表格数据"""
        data = []
        for row in range(self.rowCount()):
            row_data = {}
            for col, header in enumerate(self.headers):
                key = self.header_key_map.get(header, header)
                item = self.item(row, col)
                if item:
                    row_data[key] = item.text()
            if row_data:
                data.append(row_data)
        return data
    
    def is_editable_col(self, col):
        return self.headers[col] != "ID"
    
    def set_editable(self, editable):
        self._editing = editable
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    flags = item.flags()
                    if editable:
                        item.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
                        item.setBackground(QColor('#fffbe6'))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    else:
                        item.setFlags(Qt.ItemFlags(flags & ~Qt.ItemFlag.ItemIsEditable))
                        item.setBackground(QColor('white'))
                        font = item.font()
                        font.setBold(False)
                        item.setFont(font)
        self.viewport().update()
    
    def closeEditor(self, editor, hint):
        super().closeEditor(editor, hint)
        self.viewport().update()
    
    def currentCellChanged(self, currentRow, currentColumn, previousRow, previousColumn):
        super().currentCellChanged(currentRow, currentColumn, previousRow, previousColumn)
        if self._editing:
            # 只允许非ID列可编辑
            if self.is_editable_col(currentColumn):
                self.selectedCell = (currentRow, currentColumn)
                self.set_editable(True)
                self.editItem(self.item(currentRow, currentColumn))
            else:
                self.selectedCell = None
        self.viewport().update()
    
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.viewport().update()

class IPConfigWidget(QWidget):
    """IP配置组件"""
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget
        self.is_editing = False
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("IP配置")
        title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333; margin: 20px 0;")
        layout.addWidget(title_label)
        
        # 表格
        headers = ["ID", "IP地址", "端口", "用户名", "密码"]
        self.table = ConfigTableWidget(headers)
        layout.addWidget(self.table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setStyleSheet('''
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 5px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        ''')
        self.edit_btn.clicked.connect(self.toggle_edit)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.setStyleSheet('''
            QPushButton {
                background-color: #107c10;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 5px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0e6e0e;
            }
            QPushButton:pressed {
                background-color: #0c5c0c;
            }
        ''')
        self.save_btn.clicked.connect(self.save_config)
        self.save_btn.setEnabled(False)
        
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_config(self):
        """加载配置"""
        proxies = app_controller.get_ip_configs()
        configs = []
        for i, proxy in enumerate(proxies, 1):
            config = {
                "id": i,
                "ip": proxy.ip,
                "port": str(proxy.port),
                "username": proxy.username,
                "password": proxy.password
            }
            configs.append(config)
        self.table.load_data(configs)
    
    def toggle_edit(self):
        self.is_editing = not self.is_editing
        self.table.set_editable(self.is_editing)
        if self.is_editing:
            self.edit_btn.setText("取消")
            self.edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #fffbe6;
                    color: #107c10;
                    border: 2px solid #107c10;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f7e9b7;
                }
                QPushButton:pressed {
                    background-color: #e6d98c;
                }
            ''')
            self.save_btn.setEnabled(True)
            self.log_widget.append_log("进入IP配置编辑模式")
        else:
            self.edit_btn.setText("编辑")
            self.edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            ''')
            self.save_btn.setEnabled(False)
            self.load_config()  # 重新加载，取消编辑
            self.log_widget.append_log("取消IP配置编辑")
    
    def save_config(self):
        """保存配置"""
        data = self.table.get_data()
        for row, item in enumerate(data):
            if not all(key in item for key in ["id", "ip", "port", "username", "password"]):
                QMessageBox.warning(self, "警告", f"第{row+1}行数据格式不完整")
                return
        configs = []
        for item in data:
            config = {
                "ip": item["ip"],
                "port": item["port"],
                "username": item["username"],
                "password": item["password"]
            }
            configs.append(config)
        if app_controller.save_ip_configs(configs):
            self.is_editing = False
            self.edit_btn.setText("编辑")
            self.edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            ''')
            self.save_btn.setEnabled(False)
            self.table.set_editable(False)
            self.load_config()
            self.log_widget.append_log(f"IP配置保存成功: {len(configs)}条记录")
            QMessageBox.information(self, "成功", "IP配置保存成功")
        else:
            QMessageBox.critical(self, "错误", "IP配置保存失败")

    def exit_edit_mode(self):
        self.is_editing = False
        self.edit_btn.setText("编辑")
        self.edit_btn.setStyleSheet('''
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        ''')
        self.save_btn.setEnabled(False)
        self.table.set_editable(False)
        self.load_config()

class WalletConfigWidget(QWidget):
    """钱包配置组件"""
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget
        self.is_editing = False
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("钱包配置")
        title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333; margin: 20px 0;")
        layout.addWidget(title_label)
        
        # 表格
        headers = ["ID", "私钥", "地址"]
        self.table = ConfigTableWidget(headers)
        layout.addWidget(self.table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setStyleSheet('''
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        ''')
        self.edit_btn.clicked.connect(self.toggle_edit)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.setStyleSheet('''
            QPushButton {
                background-color: #107c10;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0e6e0e;
            }
            QPushButton:pressed {
                background-color: #0c5c0c;
            }
        ''')
        self.save_btn.clicked.connect(self.save_config)
        self.save_btn.setEnabled(False)
        
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_config(self):
        """加载配置"""
        wallets = app_controller.get_wallet_configs()
        configs = []
        for i, wallet in enumerate(wallets, 1):
            config = {
                "id": i,
                "privateKey": wallet.private_key,
                "address": wallet.address
            }
            configs.append(config)
        self.table.load_data(configs)
    
    def toggle_edit(self):
        self.is_editing = not self.is_editing
        self.table.set_editable(self.is_editing)
        if self.is_editing:
            self.edit_btn.setText("取消")
            self.edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #fffbe6;
                    color: #107c10;
                    border: 2px solid #107c10;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f7e9b7;
                }
                QPushButton:pressed {
                    background-color: #e6d98c;
                }
            ''')
            self.save_btn.setEnabled(True)
            self.log_widget.append_log("进入钱包配置编辑模式")
        else:
            self.edit_btn.setText("编辑")
            self.edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            ''')
            self.save_btn.setEnabled(False)
            self.load_config()  # 重新加载，取消编辑
            self.log_widget.append_log("取消钱包配置编辑")
    
    def save_config(self):
        """保存配置"""
        data = self.table.get_data()
        for row, item in enumerate(data):
            if not all(key in item for key in ["id", "privateKey", "address"]):
                QMessageBox.warning(self, "警告", f"第{row+1}行数据格式不完整")
                return
        configs = []
        for item in data:
            config = {
                "privateKey": item["privateKey"],
                "address": item["address"]
            }
            configs.append(config)
        if app_controller.save_wallet_configs(configs):
            self.is_editing = False
            self.edit_btn.setText("编辑")
            self.edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            ''')
            self.save_btn.setEnabled(False)
            self.table.set_editable(False)
            self.load_config()
            self.log_widget.append_log(f"钱包配置保存成功: {len(configs)}条记录")
            QMessageBox.information(self, "成功", "钱包配置保存成功")
        else:
            QMessageBox.critical(self, "错误", "钱包配置保存失败")

    def exit_edit_mode(self):
        self.is_editing = False
        self.edit_btn.setText("编辑")
        self.edit_btn.setStyleSheet('''
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        ''')
        self.save_btn.setEnabled(False)
        self.table.set_editable(False)
        self.load_config()

class BrowserConfigWidget(QWidget):
    """浏览器ID配置组件"""
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget
        self.is_editing = False
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("浏览器ID配置")
        title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333; margin: 20px 0;")
        layout.addWidget(title_label)
        
        # 说明文字
        desc_label = QLabel("第一行：API地址，第二行及以后：浏览器ID（每行一个）")
        desc_label.setFont(QFont('Microsoft YaHei', 12))
        desc_label.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(desc_label)
        
        # 文本编辑区域
        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(QFont('Consolas', 11))
        self.text_edit.setStyleSheet('''
            QPlainTextEdit {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                padding: 10px;
                line-height: 1.5;
            }
            QPlainTextEdit:focus {
                border-color: #0078d4;
            }
        ''')
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setStyleSheet('''
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        ''')
        self.edit_btn.clicked.connect(self.toggle_edit)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.setStyleSheet('''
            QPushButton {
                background-color: #107c10;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0e6e0e;
            }
            QPushButton:pressed {
                background-color: #0c5c0c;
            }
        ''')
        self.save_btn.clicked.connect(self.save_config)
        self.save_btn.setEnabled(False)
        
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_config(self):
        """加载配置"""
        content = app_controller.get_browser_configs()
        self.text_edit.setPlainText(content)
    
    def toggle_edit(self):
        self.is_editing = not self.is_editing
        if self.is_editing:
            self.text_edit.setReadOnly(False)
            self.text_edit.setStyleSheet('''
                QPlainTextEdit {
                    background-color: #fffbe6;
                    border: 2px solid #107c10;
                    border-radius: 8px;
                    padding: 10px;
                    line-height: 1.5;
                }
                QPlainTextEdit:focus {
                    border-color: #107c10;
                }
            ''')
            self.edit_btn.setText("取消")
            self.edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #fffbe6;
                    color: #107c10;
                    border: 2px solid #107c10;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f7e9b7;
                }
                QPushButton:pressed {
                    background-color: #e6d98c;
                }
            ''')
            self.save_btn.setEnabled(True)
            self.log_widget.append_log("进入浏览器ID配置编辑模式")
        else:
            self.text_edit.setReadOnly(True)
            self.text_edit.setStyleSheet('''
                QPlainTextEdit {
                    background-color: white;
                    border: 1px solid #d0d0d0;
                    border-radius: 8px;
                    padding: 10px;
                    line-height: 1.5;
                }
                QPlainTextEdit:focus {
                    border-color: #0078d4;
                }
            ''')
            self.edit_btn.setText("编辑")
            self.edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            ''')
            self.save_btn.setEnabled(False)
            self.load_config()  # 重新加载，取消编
            self.log_widget.append_log("取消浏览器ID配置编辑")
    
    def save_config(self):
        """保存配置"""
        content = self.text_edit.toPlainText()
        if app_controller.save_browser_configs(content):
            self.log_widget.append_log(f"浏览器配置保存成功")
            QMessageBox.information(self, "成功", "浏览器配置保存成功")
            self.is_editing = False
            self.edit_btn.setText("编辑")
            self.edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            ''')
            self.save_btn.setEnabled(False)
            self.text_edit.setReadOnly(True)
            self.text_edit.setStyleSheet('''
                QPlainTextEdit {
                    background-color: white;
                    border: 1px solid #d0d0d0;
                    border-radius: 8px;
                    padding: 10px;
                    line-height: 1.5;
                }
                QPlainTextEdit:focus {
                    border-color: #0078d4;
                }
            ''')
            self.load_config()
        else:
            QMessageBox.critical(self, "错误", "浏览器配置保存失败")

    def exit_edit_mode(self):
        self.is_editing = False
        self.edit_btn.setText("编辑")
        self.edit_btn.setStyleSheet('''
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        ''')
        self.save_btn.setEnabled(False)
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet('''
            QPlainTextEdit {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                padding: 10px;
                line-height: 1.5;
            }
            QPlainTextEdit:focus {
                border-color: #0078d4;
            }
        ''')
        self.load_config()

class HomeTab(QWidget):
    """首页标签页"""
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget
        self.init_ui()
        self.load_readme()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.readme_display = QTextEdit()
        self.readme_display.setReadOnly(True)
        layout.addWidget(self.readme_display)
        self.setLayout(layout)

    def load_readme(self):
        """加载并渲染README.md"""
        try:
            readme_path = resource_path('README.md')
            with open(readme_path, 'r', encoding='utf-8') as f:
                md_text = f.read()
                
            html = markdown.markdown(md_text, extensions=['fenced_code', 'tables'])
            self.readme_display.setHtml(html)
            self.log_widget.append_log("README.md 已加载到首页。")
        except Exception as e:
            self.log_widget.append_log(f"加载 README.md 失败: {e}")
            self.readme_display.setText(f"加载 README.md 失败: {e}")
        


class ConfigTab(QWidget):
    """配置标签页"""
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget
        self._last_sidebar_index = 0
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 侧边栏
        sidebar_items = ["IP配置", "钱包配置", "浏览器ID配置"]
        self.sidebar = StyledSidebar(sidebar_items, 200)
        self.sidebar.currentRowChanged.connect(self.on_sidebar_changed)
        layout.addWidget(self.sidebar)
        
        # 内容区域
        self.content_stack = QStackedWidget()
        
        # IP配置页面
        self.ip_config_widget = IPConfigWidget(self.log_widget)
        self.content_stack.addWidget(self.ip_config_widget)
        
        # 钱包配置页面
        self.wallet_config_widget = WalletConfigWidget(self.log_widget)
        self.content_stack.addWidget(self.wallet_config_widget)
        
        # 浏览器ID配置页面
        self.browser_config_widget = BrowserConfigWidget(self.log_widget)
        self.content_stack.addWidget(self.browser_config_widget)
        
        layout.addWidget(self.content_stack)
        self.setLayout(layout)
        

        
    def on_sidebar_changed(self, index):
        current_widget = self.content_stack.currentWidget()
        # 如果有编辑状态，直接还原并切换，不弹窗
        if hasattr(current_widget, 'is_editing') and current_widget.is_editing:
            current_widget.exit_edit_mode()
        self._last_sidebar_index = index
        self.content_stack.setCurrentIndex(index)
        items = ["IP配置", "钱包配置", "浏览器ID配置"]
        if 0 <= index < len(items):
            if index == 0:
                self.ip_config_widget.load_config()
            elif index == 1:
                self.wallet_config_widget.load_config()
            elif index == 2:
                self.browser_config_widget.load_config()

class ProjectTab(QWidget):
    """项目标签页，自动加载myProject下所有项目脚本"""
    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget
        self.project_classes = []
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        # 左侧sidebar，使用StyledSidebar风格
        self.sidebar = StyledSidebar([], 200)
        self.sidebar.currentRowChanged.connect(self.on_sidebar_changed)
        layout.addWidget(self.sidebar)
        # 分隔线
        splitter = QFrame()
        splitter.setFrameShape(QFrame.VLine)
        splitter.setFrameShadow(QFrame.Sunken)
        splitter.setLineWidth(2)
        layout.addWidget(splitter)
        # 右侧功能区
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack)
        self.setLayout(layout)

    def populate_projects(self, projects):
        """用从控制器获取的项目数据填充UI"""
        self.project_classes = projects
        # 清空旧项目
        self.sidebar.clear()
        while self.content_stack.count() > 0:
            widget = self.content_stack.widget(0)
            self.content_stack.removeWidget(widget)
            widget.deleteLater()
            
        # 添加新项目
        for proj in self.project_classes:
            self.sidebar.addItem(proj['project_name'])
            self.content_stack.addWidget(self.create_project_widget(proj))
            
        if self.project_classes:
            self.sidebar.setCurrentRow(0)

    def create_project_widget(self, proj):
        widget = QWidget()
        vlayout = QVBoxLayout()
        
        # 项目描述
        project_desc_label = QLabel(proj.get('project_desc', '没有项目描述。'))
        project_desc_label.setFont(QFont('Microsoft YaHei', 12))
        project_desc_label.setStyleSheet('color: #666; margin: 10px 0;')
        vlayout.addWidget(project_desc_label)

        # 一键运行所有任务按钮
        run_all_btn = QPushButton(f"一键运行 {proj['project_name']} 所有任务")
        run_all_btn.setStyleSheet('''
            QPushButton {
                background-color: #0078d4; color: white; font-weight: bold;
                font-size: 16px; padding: 12px; border-radius: 8px;
            }
            QPushButton:hover { background-color: #106ebe; }
        ''')
        # "一键运行"的功能是把该项目的所有task都分发一遍
        run_all_btn.clicked.connect(
            lambda _, p=proj: [
                app_controller.dispatch_task(p['project_name'], task['name']) for task in p['tasks']
            ]
        )
        vlayout.addWidget(run_all_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        vlayout.addWidget(line)

        # 每个task的单独运行按钮
        for task in proj['tasks']:
            task_group_layout = QHBoxLayout()
            
            task_label = QLabel(f"<b>{task['name']}</b>: {task['desc']}")
            task_label.setWordWrap(True)
            
            task_btn = QPushButton(f"运行")
            task_btn.setFixedWidth(200)
            task_btn.setStyleSheet('''
                QPushButton {
                    background-color: #107c10; color: white; font-weight: bold;
                    font-size: 18px; padding: 12px; border-radius: 8px;
                }
                QPushButton:hover { background-color: #0e6e0e; }
            ''')
            # "单独运行"的功能是只分发这一个task
            task_btn.clicked.connect(
                lambda _, p=proj, t=task: app_controller.dispatch_task(p['project_name'], t['name'])
            )
            
            task_group_layout.addWidget(task_label)
            task_group_layout.addStretch()
            task_group_layout.addWidget(task_btn)
            
            vlayout.addLayout(task_group_layout)

        vlayout.addStretch()
        widget.setLayout(vlayout)
        return widget

    def on_sidebar_changed(self, index):
        self.content_stack.setCurrentIndex(index)

class MyToolApplication(QWidget):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        # 1. 使用后端的控制器单例
        self.controller = app_controller
        self.init_ui()
        # 2. 在后台线程中启动初始化
        self.start_backend_initialization()
        
    def init_ui(self):
        # 设置窗口属性
        self.setWindowTitle("S1mpleWeb3Tool")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet('''
            QWidget {
                background-color: white;
                font-family: 'Microsoft YaHei';
            }
            QTabWidget::pane {
                border: none;
                background: white;
            }
            QTabBar::tab {
                background: #f0f0f0;
                color: #333;
                padding: 14px 36px;
                margin-right: 4px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                min-width: 120px;
                max-width: 300px;
            }
            QTabBar::tab:selected {
                background: #0078d4;
                color: white;
            }
            QTabBar::tab:hover {
                background: #e0e0e0;
            }
            QTabBar::tab:selected:hover {
                background: #0078d4;
            }
        ''')
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("QTabWidget::pane { border: none; }")
        
        # 创建日志组件
        self.log_widget = LogWidget()
        
        # 创建各个标签页
        self.home_tab = HomeTab(self.log_widget)
        self.config_tab = ConfigTab(self.log_widget)
        self.project_tab = ProjectTab(self.log_widget)
        
        # 添加标签页
        self.tab_widget.addTab(self.home_tab, "首页")
        self.tab_widget.addTab(self.config_tab, "配置")
        self.tab_widget.addTab(self.project_tab, "项目")
        
        # 标签页切换事件
        self.tab_widget.tabBarClicked.connect(self.on_tab_bar_clicked)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # 添加到主布局
        main_layout.addWidget(self.tab_widget)
        
        # 日志区域
        log_label = QLabel("日志")
        log_label.setFont(QFont('Microsoft YaHei', 12, QFont.Weight.Bold))
        log_label.setStyleSheet("color: #333; margin: 10px 0 5px 0;")
        main_layout.addWidget(log_label)
        
        main_layout.addWidget(self.log_widget)
        
        self.setLayout(main_layout)
        
        # 记录启动日志
        self.log_widget.append_log("应用程序UI已加载，正在初始化后端...")
        
        self.tab_widget.tabBar().installEventFilter(self)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def start_backend_initialization(self):
        self.init_thread = BackendInitializationThread(self.controller)
        self.init_thread.initialization_done.connect(self.on_backend_initialized)
        self.init_thread.start()

    def on_backend_initialized(self, success, message):
        self.log_widget.append_log(f"后端初始化结果: {message}")
        if success:
            # 初始化成功后，用获取到的数据填充UI
            self.project_tab.populate_projects(self.controller.projects)
            self.log_widget.append_log("项目选项卡已更新.")
        else:
            # 初始化失败，可以弹窗提示
            QMessageBox.critical(self, "后端初始化失败", message)
        
    def eventFilter(self, obj, event):
        if obj == self.tab_widget.tabBar() and event.type() == event.MouseButtonPress:
            next_index = self.tab_widget.tabBar().tabAt(event.pos())
            if next_index != self.tab_widget.currentIndex():
                # 检查所有tab下是否有未保存编辑，直接还原并切换
                for i in range(self.tab_widget.count()):
                    widget = self.tab_widget.widget(i)
                    if hasattr(widget, 'is_editing') and widget.is_editing:
                        widget.exit_edit_mode()
            return False
        return super().eventFilter(obj, event)
        
    def on_tab_bar_clicked(self, index):
        if index == self.tab_widget.currentIndex():
            return
        # 检查所有tab下是否有未保存编辑，直接还原并切换
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, 'is_editing') and widget.is_editing:
                widget.exit_edit_mode()
        self.tab_widget.setCurrentIndex(index)
        
    def on_tab_changed(self, index):
        tab_names = ["首页", "配置", "项目"]
        if 0 <= index < len(tab_names):
            pass
    
    def closeEvent(self, event):
        # 3. 在关闭时调用后端的shutdown方法
        log_util.info("UI", "应用程序正在关闭，开始释放后端资源...")
        self.controller.shutdown()
        log_util.info("UI", "后端资源已释放。")
        
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, 'is_editing') and widget.is_editing:
                widget.exit_edit_mode()
        super().closeEvent(event)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("S1mpleWeb3Tool")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("S1mpleWeb3Tool")
    
    # 创建主窗口
    window = MyToolApplication()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
