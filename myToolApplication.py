import markdown
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QTextEdit, QPushButton, QLabel, QPlainTextEdit, 
    QStackedWidget, QMessageBox,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QStyledItemDelegate, QProxyStyle, QStyle, QScrollArea, QLineEdit, QSplitter, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QFont, QColor, QPalette, QIntValidator, QIcon

# 导入后端控制器和日志工具
from applicationController import app_controller
from util.log_util import log_util

from config import AppConfig

class QtLogHandler(QObject):
    log_signal = pyqtSignal(str)

    def handle(self, msg):
        self.log_signal.emit(msg)

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
            log_util.error("Backend", f"Backend initialization failed: {e}", exc_info=True)
            self.initialization_done.emit(False, str(e))

def resource_path(relative_path):
    try:
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    except Exception as e:
        print(f"resource_path error for {relative_path}: {e}")
        return relative_path

class LogWidget(QTextEdit):
    """日志显示组件，只负责显示从回调函数传递过来的日志。"""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont('Consolas', 10))
        pal = self.palette()
        pal.setColor(QPalette.Base, QColor(245, 245, 245))
        pal.setColor(QPalette.Text, QColor(30, 30, 30))
        self.setPalette(pal)
        self.setFixedHeight(200)
    
    def append_log(self, msg):
        self.append(msg)
        sb = self.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())

class StyledSidebar(QListWidget):
    """样式化的侧边栏"""
    def __init__(self, items, width=200):
        super().__init__()
        self.setFixedWidth(width)
        self.setSpacing(8)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet('''
            QListView, QListWidget { outline: none; }
            QListWidget { border: none; background: transparent; }
            QListWidget::item { background: #f0f0f0; border: 1px solid #d0d0d0; border-radius: 8px; margin: 4px 0; padding: 12px 16px; font-size: 14px; color: #333; font-weight: 500; }
            QListWidget::item:hover { background: #e0e0e0; border-color: #b0b0b0; }
            QListWidget::item:selected { background: #0078d4; color: white; border-color: #0078d4; }
        ''')
        for item_text in items:
            self.addItem(item_text)
        if self.count() > 0:
            self.setCurrentRow(0)

class NoFocusRectStyle(QProxyStyle):
    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect: return
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
    header_key_map = { "ID": "id", "IP地址": "ip", "端口": "port", "用户名": "username", "密码": "password", "私钥": "privateKey", "地址": "address" }
    def __init__(self, headers, data=None):
        super().__init__()
        self.headers = headers
        self._editing = False
        self.setItemDelegate(EditModeDelegate(self, lambda: self._editing))
        self.setStyle(NoFocusRectStyle(self.style()))
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setStyleSheet('''
            QTableWidget { background-color: white; border: 1px solid #d0d0d0; border-radius: 12px; gridline-color: #e0e0e0; }
            QTableWidget::item { padding: 8px; border: none; border-radius: 8px; background: transparent; }
            QTableWidget::item:selected { background: transparent; border: 2px solid orange; color: #333; }
            QTableWidget::item:focus { outline: none; }
            QHeaderView::section { background-color: #f8f9fa; padding: 8px; border: none; border-bottom: 1px solid #d0d0d0; font-weight: bold; font-size: 15px; }
        ''')
        for i, h in enumerate(headers):
            if h == "ID":
                self.setColumnWidth(i, 60)
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)
            else:
                self.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        self.horizontalHeader().setStretchLastSection(True)
        if data: self.load_data(data)
    
    def load_data(self, data):
        self.setRowCount(len(data))
        for row, item in enumerate(data):
            for col, header in enumerate(self.headers):
                key = self.header_key_map.get(header, header)
                if key in item:
                    value = str(item[key])
                    table_item = QTableWidgetItem(value)
                    table_item.setFlags(Qt.ItemFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable))
                    self.setItem(row, col, table_item)
    
    def get_data(self):
        data = []
        for row in range(self.rowCount()):
            row_data = {}
            for col, header in enumerate(self.headers):
                key = self.header_key_map.get(header, header)
                item = self.item(row, col)
                if item: row_data[key] = item.text()
            if row_data: data.append(row_data)
        return data
    
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
                        font = item.font(); font.setBold(True); item.setFont(font)
                    else:
                        item.setFlags(Qt.ItemFlags(flags & ~Qt.ItemFlag.ItemIsEditable))
                        item.setBackground(QColor('white'))
                        font = item.font(); font.setBold(False); item.setFont(font)
        self.viewport().update()

class IPConfigWidget(QWidget):
    """IP配置组件"""
    def __init__(self):
        super().__init__()
        self.is_editing = False
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        layout = QVBoxLayout()
        title_label = QLabel("IP配置"); title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold)); title_label.setStyleSheet("color: #333; margin: 20px 0;"); layout.addWidget(title_label)
        headers = ["ID", "IP地址", "端口", "用户名", "密码"]; self.table = ConfigTableWidget(headers); layout.addWidget(self.table)
        button_layout = QHBoxLayout()
        self.edit_btn = QPushButton("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.edit_btn.clicked.connect(self.toggle_edit)
        self.save_btn = QPushButton("保存"); self.save_btn.setStyleSheet(''' QPushButton { background-color: #107c10; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #0e6e0e; } QPushButton:pressed { background-color: #0c5c0c; } '''); self.save_btn.clicked.connect(self.save_config); self.save_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn); button_layout.addWidget(self.save_btn); button_layout.addStretch(); layout.addLayout(button_layout); self.setLayout(layout)
    
    def load_config(self):
        proxies = app_controller.get_ip_configs()
        configs = [{"id": i, "ip": p.ip, "port": str(p.port), "username": p.username, "password": p.password} for i, p in enumerate(proxies, 1)]
        self.table.load_data(configs)
    
    def toggle_edit(self):
        self.is_editing = not self.is_editing
        self.table.set_editable(self.is_editing)
        if self.is_editing:
            self.edit_btn.setText("取消"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #fffbe6; color: #107c10; border: 2px solid #107c10; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #f7e9b7; } QPushButton:pressed { background-color: #e6d98c; } '''); self.save_btn.setEnabled(True); log_util.info("UI", "进入IP配置编辑模式")
        else:
            self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.load_config(); log_util.info("UI", "取消IP配置编辑")
    
    def save_config(self):
        data = self.table.get_data()
        configs = [{"ip": item["ip"], "port": item["port"], "username": item["username"], "password": item["password"]} for item in data]
        if app_controller.save_ip_configs(configs):
            self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.table.set_editable(False); self.load_config(); QMessageBox.information(self, "成功", "IP配置保存成功")
        else: QMessageBox.critical(self, "错误", "IP配置保存失败")

    def exit_edit_mode(self):
        self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.table.set_editable(False); self.load_config()

class WalletConfigWidget(QWidget):
    """钱包配置组件"""
    def __init__(self):
        super().__init__()
        self.is_editing = False
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        layout = QVBoxLayout()
        title_label = QLabel("钱包配置"); title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold)); title_label.setStyleSheet("color: #333; margin: 20px 0;"); layout.addWidget(title_label)
        headers = ["ID", "私钥", "地址"]; self.table = ConfigTableWidget(headers); layout.addWidget(self.table)
        button_layout = QHBoxLayout()
        self.edit_btn = QPushButton("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.edit_btn.clicked.connect(self.toggle_edit)
        self.save_btn = QPushButton("保存"); self.save_btn.setStyleSheet(''' QPushButton { background-color: #107c10; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #0e6e0e; } QPushButton:pressed { background-color: #0c5c0c; } '''); self.save_btn.clicked.connect(self.save_config); self.save_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn); button_layout.addWidget(self.save_btn); button_layout.addStretch(); layout.addLayout(button_layout); self.setLayout(layout)
    
    def load_config(self):
        wallets = app_controller.get_wallet_configs()
        configs = [{"id": i, "privateKey": w.private_key, "address": w.address} for i, w in enumerate(wallets, 1)]
        self.table.load_data(configs)
    
    def toggle_edit(self):
        self.is_editing = not self.is_editing
        self.table.set_editable(self.is_editing)
        if self.is_editing:
            self.edit_btn.setText("取消"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #fffbe6; color: #107c10; border: 2px solid #107c10; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #f7e9b7; } QPushButton:pressed { background-color: #e6d98c; } '''); self.save_btn.setEnabled(True); log_util.info("UI", "进入钱包配置编辑模式")
        else:
            self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.load_config(); log_util.info("UI", "取消钱包配置编辑")
    
    def save_config(self):
        data = self.table.get_data()
        configs = [{"privateKey": item["privateKey"], "address": item["address"]} for item in data]
        if app_controller.save_wallet_configs(configs):
            self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.table.set_editable(False); self.load_config(); QMessageBox.information(self, "成功", "钱包配置保存成功")
        else: QMessageBox.critical(self, "错误", "钱包配置保存失败")

    def exit_edit_mode(self):
        self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.table.set_editable(False); self.load_config()

class BrowserConfigWidget(QWidget):
    """浏览器ID配置组件"""
    def __init__(self):
        super().__init__()
        self.is_editing = False
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        layout = QVBoxLayout()
        title_label = QLabel("浏览器ID配置"); title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold)); title_label.setStyleSheet("color: #333; margin: 20px 0;"); layout.addWidget(title_label)
        desc_label = QLabel("第一行：API地址，第二行及以后：浏览器ID（每行一个）"); desc_label.setFont(QFont('Microsoft YaHei', 12)); desc_label.setStyleSheet("color: #666; margin: 10px 0;"); layout.addWidget(desc_label)
        self.text_edit = QPlainTextEdit(); self.text_edit.setFont(QFont('Consolas', 11)); self.text_edit.setStyleSheet(''' QPlainTextEdit { background-color: white; border: 1px solid #d0d0d0; border-radius: 8px; padding: 10px; line-height: 1.5; } QPlainTextEdit:focus { border-color: #0078d4; } '''); self.text_edit.setReadOnly(True); layout.addWidget(self.text_edit)
        button_layout = QHBoxLayout()
        self.edit_btn = QPushButton("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.edit_btn.clicked.connect(self.toggle_edit)
        self.save_btn = QPushButton("保存"); self.save_btn.setStyleSheet(''' QPushButton { background-color: #107c10; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #0e6e0e; } QPushButton:pressed { background-color: #0c5c0c; } '''); self.save_btn.clicked.connect(self.save_config); self.save_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn); button_layout.addWidget(self.save_btn); button_layout.addStretch(); layout.addLayout(button_layout); self.setLayout(layout)
    
    def load_config(self):
        content = app_controller.get_browser_configs()
        self.text_edit.setPlainText(content)
    
    def toggle_edit(self):
        self.is_editing = not self.is_editing
        if self.is_editing:
            self.text_edit.setReadOnly(False); self.text_edit.setStyleSheet(''' QPlainTextEdit { background-color: #fffbe6; border: 2px solid #107c10; border-radius: 8px; padding: 10px; line-height: 1.5; } QPlainTextEdit:focus { border-color: #107c10; } '''); self.edit_btn.setText("取消"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #fffbe6; color: #107c10; border: 2px solid #107c10; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #f7e9b7; } QPushButton:pressed { background-color: #e6d98c; } '''); self.save_btn.setEnabled(True); log_util.info("UI", "进入浏览器ID配置编辑模式")
        else:
            self.text_edit.setReadOnly(True); self.text_edit.setStyleSheet(''' QPlainTextEdit { background-color: white; border: 1px solid #d0d0d0; border-radius: 8px; padding: 10px; line-height: 1.5; } QPlainTextEdit:focus { border-color: #0078d4; } '''); self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.load_config(); log_util.info("UI", "取消浏览器ID配置编辑")
    
    def save_config(self):
        content = self.text_edit.toPlainText()
        if app_controller.save_browser_configs(content):
            log_util.info("UI", f"浏览器配置保存成功"); QMessageBox.information(self, "成功", "浏览器配置保存成功"); self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.text_edit.setReadOnly(True); self.text_edit.setStyleSheet(''' QPlainTextEdit { background-color: white; border: 1px solid #d0d0d0; border-radius: 8px; padding: 10px; line-height: 1.5; } QPlainTextEdit:focus { border-color: #0078d4; } '''); self.load_config()
        else: QMessageBox.critical(self, "错误", "浏览器配置保存失败")

    def exit_edit_mode(self):
        self.is_editing = False; self.edit_btn.setText("编辑"); self.edit_btn.setStyleSheet(''' QPushButton { background-color: #0078d4; color: white; border: none; padding: 15px 30px; border-radius: 5px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #106ebe; } QPushButton:pressed { background-color: #005a9e; } '''); self.save_btn.setEnabled(False); self.text_edit.setReadOnly(True); self.text_edit.setStyleSheet(''' QPlainTextEdit { background-color: white; border: 1px solid #d0d0d0; border-radius: 8px; padding: 10px; line-height: 1.5; } QPlainTextEdit:focus { border-color: #0078d4; } '''); self.load_config()

class HomeTab(QWidget):
    """首页标签页"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_readme()
        
    def init_ui(self):
        layout = QVBoxLayout(); self.readme_display = QTextEdit(); self.readme_display.setReadOnly(True); layout.addWidget(self.readme_display); self.setLayout(layout)

    def load_readme(self):
        try:
            readme_path = resource_path('README.md')
            with open(readme_path, 'r', encoding='utf-8') as f: md_text = f.read()
            css = """<style> body { font-family: 'Microsoft YaHei'; font-size: 16px; line-height: 1.6; } h1 { font-size: 28px; color: #0078d4; border-bottom: 2px solid #0078d4; padding-bottom: 10px; } h2 { font-size: 24px; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-top: 20px;} h3 { font-size: 20px; } code { font-family: 'Consolas', 'Courier New', monospace; background-color: #f0f0f0; padding: 2px 4px; border-radius: 4px; } pre { background-color: #f5f5f5; border: 1px solid #ccc; border-radius: 4px; padding: 10px; white-space: pre-wrap; word-wrap: break-word; } pre > code { background-color: transparent; padding: 0; } ul, ol { padding-left: 20px; } </style>"""
            html = markdown.markdown(md_text, extensions=['fenced_code', 'tables'])
            self.readme_display.setHtml(css + html)
            log_util.info("UI", "README.md 已加载到首页。")
        except Exception as e:
            log_util.error("UI", f"加载 README.md 失败: {e}")
            self.readme_display.setText(f"加载 README.md 失败: {e}")

class ConfigTab(QWidget):
    """配置标签页"""
    def __init__(self):
        super().__init__()
        self._last_sidebar_index = 0
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        sidebar_items = ["IP配置", "钱包配置", "浏览器ID配置"]; self.sidebar = StyledSidebar(sidebar_items, 200); self.sidebar.currentRowChanged.connect(self.on_sidebar_changed); layout.addWidget(self.sidebar)
        self.content_stack = QStackedWidget()
        self.ip_config_widget = IPConfigWidget(); self.content_stack.addWidget(self.ip_config_widget)
        self.wallet_config_widget = WalletConfigWidget(); self.content_stack.addWidget(self.wallet_config_widget)
        self.browser_config_widget = BrowserConfigWidget(); self.content_stack.addWidget(self.browser_config_widget)
        layout.addWidget(self.content_stack); self.setLayout(layout)
        
    def on_sidebar_changed(self, index):
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'is_editing') and current_widget.is_editing: current_widget.exit_edit_mode()
        self._last_sidebar_index = index; self.content_stack.setCurrentIndex(index)
        items = ["IP配置", "钱包配置", "浏览器ID配置"]
        if 0 <= index < len(items):
            if index == 0: self.ip_config_widget.load_config()
            elif index == 1: self.wallet_config_widget.load_config()
            elif index == 2: self.browser_config_widget.load_config()

class SequenceItemWidget(QWidget):
    """任务序列中的自定义条目控件"""
    remove_requested = pyqtSignal(QListWidgetItem)

    def __init__(self, project_name, task_name, count, list_item):
        super().__init__()
        self.project_name = project_name
        self.task_name = task_name
        self.count = count
        self.list_item = list_item
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        # Left-aligned task name
        task_name_label = QLabel(f"<b>{self.task_name}</b>")
        task_name_label.setStyleSheet("font-size: 25px;")
        # Right-aligned count and remove button
        count_label = QLabel(f"执行 {self.count} 次")
        count_label.setStyleSheet("color: #555; font-size: 20px;")

        remove_btn = QPushButton("移除")
        remove_btn.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 4px; padding: 8px 16px; margin-left: 10px;")
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.list_item))

        layout.addWidget(task_name_label)
        layout.addStretch()
        layout.addWidget(count_label)
        layout.addWidget(remove_btn)

    def get_sequence_data(self):
        return {
            'task_name': self.task_name,
            'repetition': self.count # Use repetition
        }

class TaskDispatchThread(QThread):
    """专门用于在后台分发任务并等待其完成的线程，以防阻塞UI主线程"""
    finished = pyqtSignal() # Signal to indicate completion

    def __init__(self, controller, sequence):
        super().__init__()
        self.controller = controller
        self.sequence = sequence

    def run(self):
        try:
            self.controller.dispatch_sequence(self.sequence)
        finally:
            self.finished.emit()

class ProjectTab(QWidget):
    """项目标签页，采用两栏布局，左侧为可用任务，右侧为任务序列"""
    def __init__(self):
        super().__init__()
        self.project_classes = []
        self.dispatch_thread = None
        self.is_running = False # State lock
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # --- Left Panel: Available Projects and Tasks ---
        left_panel = QWidget()
        left_layout = QHBoxLayout(left_panel)
        
        self.sidebar = StyledSidebar([], 200)
        self.sidebar.currentRowChanged.connect(self.on_sidebar_changed)
        
        self.content_stack = QStackedWidget()

        left_layout.addWidget(self.sidebar)
        left_layout.addWidget(self.content_stack)
        
        # --- Right Panel: Task Sequence ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 20, 10, 10)

        seq_title = QLabel("任务执行序列")
        seq_title.setFont(QFont('Microsoft YaHei', 14, QFont.Weight.Bold))
        seq_title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")

        self.sequence_list = QListWidget()
        self.sequence_list.setStyleSheet("QListWidget { border: 1px solid #ccc; border-radius: 8px; }")
        self.sequence_list.setSpacing(8)

        # Action Buttons
        action_layout = QHBoxLayout()
        self.stop_btn = QPushButton("停止执行")
        self.stop_btn.setStyleSheet("background-color: #d35400; color: white; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.stop_btn.clicked.connect(app_controller.interrupt_tasks)
        self.stop_btn.setEnabled(False) # Initially disabled

        self.run_seq_btn = QPushButton("执行序列")
        self.run_seq_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.run_seq_btn.clicked.connect(self.on_run_sequence_clicked)

        self.clear_seq_btn = QPushButton("清空序列")
        self.clear_seq_btn.setStyleSheet("background-color: #95a5a6; color: white; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.clear_seq_btn.clicked.connect(self.sequence_list.clear)
        
        action_layout.addWidget(self.stop_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.clear_seq_btn)
        action_layout.addWidget(self.run_seq_btn)

        right_layout.addWidget(seq_title)
        right_layout.addWidget(self.sequence_list)
        right_layout.addLayout(action_layout)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([750, 250])
        main_layout.addWidget(splitter)

    def populate_projects(self, projects):
        self.project_classes = projects
        self.sidebar.clear()
        while self.content_stack.count() > 0:
            widget = self.content_stack.widget(0)
            self.content_stack.removeWidget(widget)
            widget.deleteLater()
        
        for proj in self.project_classes:
            self.sidebar.addItem(proj['project_name'])
            self.content_stack.addWidget(self.create_available_tasks_widget(proj))
        
        if self.project_classes:
            self.sidebar.setCurrentRow(0)

    def create_available_tasks_widget(self, proj):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        project_desc_label = QLabel(proj.get('project_desc', '没有项目描述。'))
        project_desc_label.setFont(QFont('Microsoft YaHei', 14, QFont.Weight.Bold))
        project_desc_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        project_desc_label.setWordWrap(True)
        main_layout.addWidget(project_desc_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_content = QWidget()
        tasks_layout = QVBoxLayout(scroll_content)
        tasks_layout.setContentsMargins(0, 0, 0, 0)
        tasks_layout.setSpacing(10)

        for task in proj['tasks']:
            task_frame = QFrame()
            task_frame.setStyleSheet("background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px;")
            task_frame_layout = QVBoxLayout(task_frame)

            top_row_layout = QHBoxLayout()
            task_name_label = QLabel(f"<b>任务:</b> {task['name']}")
            task_name_label.setFont(QFont('Microsoft YaHei', 12, QFont.Weight.Bold))
            
            top_row_layout.addWidget(task_name_label)
            top_row_layout.addStretch()

            count_input = QLineEdit("1")
            count_input.setFixedWidth(100)
            count_input.setValidator(QIntValidator(1, 99))
            count_input.setAlignment(Qt.AlignCenter)
            if task.get('limit') == 'once_per_day':
                count_input.setEnabled(False)

            add_btn = QPushButton("添加")
            add_btn.setFixedWidth(80)
            add_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
            add_btn.clicked.connect(lambda _, p=proj, t=task, i=count_input: self.add_task_to_sequence(p, t, i))

            add_label = QLabel("添加")
            add_label.setStyleSheet("border: none; background-color: transparent;")
            suffix_label = QLabel("次到执行序列")
            suffix_label.setStyleSheet("border: none; background-color: transparent;")

            top_row_layout.addWidget(add_label)
            top_row_layout.addWidget(count_input)
            top_row_layout.addWidget(suffix_label)
            top_row_layout.addWidget(add_btn)

            task_frame_layout.addLayout(top_row_layout)

            task_desc_label = QLabel(task.get('desc', '没有任务描述。').strip())
            task_desc_label.setFont(QFont('Microsoft YaHei', 10))
            task_desc_label.setWordWrap(True)
            task_desc_label.setStyleSheet("color: #7f8c8d; margin-top: 8px;")
            task_frame_layout.addWidget(task_desc_label)
            
            tasks_layout.addWidget(task_frame)

        tasks_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        return widget

    def add_task_to_sequence(self, project, task, count_input):
        if self.is_running:
            QMessageBox.warning(self, "操作无效", "任务正在执行时，无法修改任务序列。")
            return

        count_text = count_input.text()
        if not count_text.isdigit() or not (1 <= int(count_text) <= 99):
            QMessageBox.warning(self, "输入无效", "执行次数必须是 1 到 99 之间的整数。")
            return

        count = int(count_text)

        for i in range(self.sequence_list.count()):
            item = self.sequence_list.item(i)
            widget = self.sequence_list.itemWidget(item)
            if widget and widget.project_name == project['project_name'] and widget.task_name == task['name']:
                self.sequence_list.takeItem(i)
                break

        list_item = QListWidgetItem(self.sequence_list)
        item_widget = SequenceItemWidget(project['project_name'], task['name'], count, list_item)
        item_widget.remove_requested.connect(self.remove_item_from_sequence)
        
        list_item.setSizeHint(item_widget.sizeHint())
        self.sequence_list.addItem(list_item)
        self.sequence_list.setItemWidget(list_item, item_widget)

    def remove_item_from_sequence(self, list_item):
        if self.is_running:
            QMessageBox.warning(self, "操作无效", "任务正在执行时，无法修改任务序列。")
            return
        row = self.sequence_list.row(list_item)
        self.sequence_list.takeItem(row)

    def on_sidebar_changed(self, index):
        self.content_stack.setCurrentIndex(index)

    def on_run_sequence_clicked(self):
        if self.is_running:
            return # Should not happen as button is disabled, but as a safeguard

        sequence_data = []
        for i in range(self.sequence_list.count()):
            item = self.sequence_list.item(i)
            widget = self.sequence_list.itemWidget(item)
            if widget:
                sequence_data.append(widget.get_sequence_data())
        
        if not sequence_data:
            QMessageBox.information(self, "序列为空", "请先将任务添加到执行序列。")
            return

        # --- Lock and run ---
        self.is_running = True
        self.update_button_states()
        app_controller.interrupt_event.clear()

        log_util.info("UI", f"任务序列已提交给后端执行，共 {len(sequence_data)} 个任务。")
        QMessageBox.information(self, "任务开始", f"开始执行任务。")
        
        self.dispatch_thread = TaskDispatchThread(app_controller, sequence_data)
        self.dispatch_thread.finished.connect(self.on_sequence_finished)
        self.dispatch_thread.start()

    def on_sequence_finished(self):
        self.is_running = False
        self.update_button_states()
        self.sequence_list.clear() # Automatically clear the sequence
        log_util.info("UI", "任务序列已全部执行完毕，并已清空显示列表。")
        QMessageBox.information(self, "任务完成", "任务序列已全部执行完毕。")

    def update_button_states(self):
        self.run_seq_btn.setEnabled(not self.is_running)
        self.clear_seq_btn.setEnabled(not self.is_running)
        self.stop_btn.setEnabled(self.is_running)




class MyToolApplication(QWidget):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        self.controller = app_controller
        self.init_ui()
        self.start_backend_initialization()
        
    def init_ui(self):
        self.setWindowTitle(f"{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
        self.setWindowIcon(QIcon(resource_path('icon/app-icon.png')))
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(''' QWidget { background-color: white; font-family: 'Microsoft YaHei'; } QTabWidget::pane { border: none; background: white; } QTabBar::tab { background: #f0f0f0; color: #333; padding: 14px 36px; margin-right: 4px; border-top-left-radius: 12px; border-top-right-radius: 12px; font-size: 18px; font-weight: bold; min-width: 120px; max-width: 300px; } QTabBar::tab:selected { background: #0078d4; color: white; } QTabBar::tab:hover { background: #e0e0e0; } QTabBar::tab:selected:hover { background: #0078d4; } ''')
        main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget(); self.tab_widget.setStyleSheet("QTabWidget::pane { border: none; }")
        self.log_widget = LogWidget()
        self.home_tab = HomeTab(); self.config_tab = ConfigTab(); self.project_tab = ProjectTab()
        self.tab_widget.addTab(self.home_tab, "首页"); self.tab_widget.addTab(self.config_tab, "配置"); self.tab_widget.addTab(self.project_tab, "项目")
        self.tab_widget.tabBarClicked.connect(self.on_tab_bar_clicked); self.tab_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_widget)
        log_label = QLabel("日志"); log_label.setFont(QFont('Microsoft YaHei', 12, QFont.Weight.Bold)); log_label.setStyleSheet("color: #333; margin: 10px 0 5px 0;"); main_layout.addWidget(log_label)
        main_layout.addWidget(self.log_widget); self.setLayout(main_layout)

        # 设置线程安全的日志处理器
        log_handler = QtLogHandler()
        log_handler.log_signal.connect(self.log_widget.append)
        log_util.add_ui_handler(log_handler.handle)

        log_util.info("UI", "应用程序UI已加载，正在初始化后端...")
        self.tab_widget.tabBar().installEventFilter(self); self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def start_backend_initialization(self):
        self.init_thread = BackendInitializationThread(self.controller)
        self.init_thread.initialization_done.connect(self.on_backend_initialized)
        self.init_thread.start()

    def on_backend_initialized(self, success, message):
        log_util.info("UI", f"后端初始化结果: {message}")
        if success:
            self.project_tab.populate_projects(self.controller.projects); log_util.info("UI", "项目选项卡已更新.")
        else: QMessageBox.critical(self, "后端初始化失败", message)
        
    def on_tab_bar_clicked(self, index):
        if index == self.tab_widget.currentIndex(): return
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, 'is_editing') and widget.is_editing: widget.exit_edit_mode()
        self.tab_widget.setCurrentIndex(index)
        
    def on_tab_changed(self, index):
        pass
    
    def closeEvent(self, event):
        log_util.info("UI", "应用程序正在关闭，开始释放后端资源...")
        self.controller.shutdown()
        log_util.shutdown()
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, 'is_editing') and widget.is_editing: widget.exit_edit_mode()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(AppConfig.APP_NAME)
    app.setApplicationVersion(AppConfig.APP_VERSION)
    app.setOrganizationName(AppConfig.APP_NAME)
    window = MyToolApplication()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()