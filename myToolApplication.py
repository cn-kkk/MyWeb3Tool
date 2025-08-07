import markdown
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QTextEdit, QPushButton, QLabel, QPlainTextEdit, 
    QStackedWidget, QMessageBox, QComboBox,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QStyledItemDelegate, QProxyStyle, QStyle, QScrollArea, QLineEdit, QSplitter, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QIntValidator, QIcon, QMovie

# 导入后端控制器和日志工具
from backend.smart_controller import SmartController

app_controller = SmartController()
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
            self.projects = self.controller.discover_projects()
            self.initialization_done.emit(True, "后端初始化成功.")
        except Exception as e:
            log_util.error("Backend", f"Backend initialization failed: {e}", exc_info=True)
            self.initialization_done.emit(False, str(e))



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

class StyledTableWidget(QTableWidget):
    """一个带有预设样式的可复用表格组件基类"""
    def __init__(self, headers):
        super().__init__()
        self.headers = headers
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setStyle(NoFocusRectStyle(self.style()))
        self.setStyleSheet('''
            QTableWidget {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 12px;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 10px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #e6f7ff;
                color: #333;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #d0d0d0;
                font-weight: bold;
                font-size: 14px;
            }
        ''')

class ConfigTableWidget(StyledTableWidget):
    """配置表格组件，现在继承自StyledTableWidget"""
    header_key_map = { "ID": "id", "IP地址": "ip", "端口": "port", "用户名": "username", "密码": "password", "私钥": "privateKey", "地址": "address" }
    def __init__(self, headers, data=None):
        super().__init__(headers)
        self._editing = False
        self.setItemDelegate(EditModeDelegate(self, lambda: self._editing))
        # 继承了通用样式，但可以添加或覆盖特定样式
        self.setStyleSheet(self.styleSheet() + '''
            QTableWidget::item:selected {
                background: transparent;
                border: 2px solid orange;
            }
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
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app # 持有主窗口引用
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
        # 解析并更新主窗口的“全局”变量
        lines = content.strip().split('\n')
        self.main_app.loaded_browser_ids = [line.strip() for line in lines[1:] if line.strip()]
    
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
            readme_path = os.path.join(AppConfig.BASE_DIR, 'README.md')
            with open(readme_path, 'r', encoding='utf-8') as f: md_text = f.read()
            css = """<style> body { font-family: 'Microsoft YaHei'; font-size: 16px; line-height: 1.6; } h1 { font-size: 28px; color: #0078d4; border-bottom: 2px solid #0078d4; padding-bottom: 10px; } h2 { font-size: 24px; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-top: 20px;} h3 { font-size: 20px; } code { font-family: 'Consolas', 'Courier New', monospace; background-color: #f0f0f0; padding: 2px 4px; border-radius: 4px; } pre { background-color: #f5f5f5; border: 1px solid #ccc; border-radius: 4px; padding: 10px; white-space: pre-wrap; word-wrap: break-word; } pre > code { background-color: transparent; padding: 0; } ul, ol { padding-left: 20px; } </style>"""
            html = markdown.markdown(md_text, extensions=['fenced_code', 'tables'])
            self.readme_display.setHtml(css + html)
            log_util.info("UI", "README.md 已加载到首页。")
        except Exception as e:
            log_util.error("UI", f"加载 README.md 失败: {e}", exc_info=True)
            self.readme_display.setText(f"加载 README.md 失败: {e}")

class ConfigTab(QWidget):
    """配置标签页"""
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app # 持有主窗口引用
        self._last_sidebar_index = 0
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        sidebar_items = ["IP配置", "钱包配置", "浏览器ID配置"]; self.sidebar = StyledSidebar(sidebar_items, 200); self.sidebar.currentRowChanged.connect(self.on_sidebar_changed); layout.addWidget(self.sidebar)
        self.content_stack = QStackedWidget()
        self.ip_config_widget = IPConfigWidget()
        self.content_stack.addWidget(self.ip_config_widget)
        self.wallet_config_widget = WalletConfigWidget()
        self.content_stack.addWidget(self.wallet_config_widget)
        self.browser_config_widget = BrowserConfigWidget(self.main_app) # 传递主窗口引用
        self.content_stack.addWidget(self.browser_config_widget)
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
    def __init__(self, controller, sequence, concurrent_browsers):
        super().__init__()
        self.controller = controller
        self.sequence = sequence
        self.concurrent_browsers = concurrent_browsers

    def run(self):
        self.controller.dispatch_sequence(self.sequence, self.concurrent_browsers)

class ProjectTab(QWidget):
    """项目标签页，采用两栏布局，左侧为可用任务，右侧为任务序列"""
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app # 持有主窗口引用
        self.results_tab = main_app.results_tab # 从主窗口获取结果页引用
        self.project_classes = []
        self.dispatch_thread = None
        self.is_running = False # State lock
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.query_progress)
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # --- Left Panel: Available Projects and Tasks ---
        left_panel = QWidget()
        left_layout = QHBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # --- Combined Sidebar Panel ---
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(260)
        sidebar_container_layout = QVBoxLayout(sidebar_container)
        sidebar_container_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_container_layout.setSpacing(15)
        sidebar_container_layout.setAlignment(Qt.AlignTop)

        # Concurrency settings
        concurrency_layout = QHBoxLayout()
        concurrency_label = QLabel("<b>最多同步浏览器:</b>")
        concurrency_label.setStyleSheet("font-size: 15px;")
        concurrency_layout.addWidget(concurrency_label)
        self.concurrency_combo = QComboBox()
        self.concurrency_combo.addItems(["2", "4", "6", "8"])
        self.concurrency_combo.setCurrentText("4")
        self.concurrency_combo.setFixedWidth(65)
        concurrency_layout.addWidget(self.concurrency_combo)
        concurrency_layout.addWidget(QLabel("个"))
        concurrency_layout.addStretch()
        sidebar_container_layout.addLayout(concurrency_layout)

        # Horizontal Separator
        h_separator = QFrame()
        h_separator.setFrameShape(QFrame.HLine)
        h_separator.setStyleSheet("border: none; border-top: 1px solid #e8e8e8;")
        sidebar_container_layout.addWidget(h_separator)

        # Project list
        self.sidebar = StyledSidebar([], 200)
        self.sidebar.currentRowChanged.connect(self.on_sidebar_changed)
        sidebar_container_layout.addWidget(self.sidebar)

        # --- Vertical Separator ---
        v_separator = QFrame()
        v_separator.setFrameShape(QFrame.VLine)
        v_separator.setStyleSheet("border: none; border-left: 1px solid #e8e8e8;")

        # --- Content Stack ---
        self.content_stack = QStackedWidget()

        # Final assembly
        left_layout.addWidget(sidebar_container)
        left_layout.addWidget(v_separator)
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
        self.stop_btn.clicked.connect(self.on_stop_clicked)
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

        # --- 组装初始任务数据并更新UI ---
        browser_ids = self.main_app.loaded_browser_ids
        initial_tasks = []
        for task_item in sequence_data:
            for browser_id in browser_ids:
                for _ in range(task_item.get('repetition', 1)):
                    initial_tasks.append({
                        'browser_id': browser_id,
                        'task_name': task_item['task_name']
                    })
        self.results_tab.populate_initial_tasks(initial_tasks)

        log_util.info("UI", f"任务序列已提交给后端执行，共 {len(sequence_data)} 个任务。")
        QMessageBox.information(self, "任务开始", f"开始执行任务。")

        concurrent_browsers = int(self.concurrency_combo.currentText())
        self.dispatch_thread = TaskDispatchThread(app_controller, sequence_data, concurrent_browsers)
        self.dispatch_thread.start()
        self.progress_timer.start(2000) # 每2秒查询一次进度

    def on_sequence_finished(self):
        self.progress_timer.stop()
        self.is_running = False
        self.update_button_states()
        self.sequence_list.clear() # Automatically clear the sequence
        log_util.info("UI", "任务序列已全部执行完毕，并已清空显示列表。")
        QMessageBox.information(self, "任务完成", "任务序列已全部执行完毕。")

    def query_progress(self):
        progress_data = app_controller.get_task_progress()
        if progress_data:
            self.results_tab.update_task_progress(progress_data)

        status = app_controller.get_execution_status()
        if status['total'] > 0 and status['completed'] >= status['total']:
            self.on_sequence_finished()

    def update_button_states(self):
        self.run_seq_btn.setEnabled(not self.is_running)
        self.clear_seq_btn.setEnabled(not self.is_running)
        self.stop_btn.setEnabled(self.is_running)

    def on_stop_clicked(self):
        """处理停止按钮点击事件，增加确认弹窗。"""
        reply = QMessageBox.question(self, '确认停止',
                                     "您确定要停止执行任务吗？\n\n此操作将终止所有未开始的任务。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            log_util.info("UI", "用户确认停止，正在向后端发送中断信号...")
            app_controller.shutdown()
        else:
            log_util.info("UI", "用户取消了停止操作。")


class TotalProgressWidget(QWidget):
    """任务总进度视图的专用控件。"""
    def __init__(self):
        super().__init__()
        self.task_row_map = {}  # 用于快速查找任务对应的行
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        headers = ['序号', '浏览器id', '任务名称', '执行结果', '失败详情', '完成时间']
        self.table = StyledTableWidget(headers)
        # FIX: Set selection to single, full rows to fix all selection bugs
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        # FIX: Ensure no cell can ever be edited
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        header = self.table.horizontalHeader()
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

    def populate_initial_tasks(self, tasks_data):
        tasks_data.sort(key=lambda x: x['browser_id'])
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        self.task_row_map.clear()
        self.table.setRowCount(len(tasks_data))

        last_browser_id = None
        for i, task in enumerate(tasks_data):
            browser_id = task['browser_id']
            task_name = task['task_name']

            # FIX: Only show browser_id if it's the first in a new group
            display_browser_id = browser_id if browser_id != last_browser_id else ""
            last_browser_id = browser_id

            # FIX: Create items with simple text, no icons or animations
            seq_item = QTableWidgetItem(str(i + 1))
            id_item = QTableWidgetItem(display_browser_id)
            name_item = QTableWidgetItem(task_name)
            result_item = QTableWidgetItem("执行中...")
            details_item = QTableWidgetItem("")
            time_item = QTableWidgetItem("")

            # FIX: Set ALL items as non-editable immediately after creation
            for item in [seq_item, id_item, name_item, result_item, details_item, time_item]:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            seq_item.setTextAlignment(Qt.AlignCenter)
            id_item.setTextAlignment(Qt.AlignCenter)
            result_item.setTextAlignment(Qt.AlignCenter)
            time_item.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(i, 0, seq_item)
            self.table.setItem(i, 1, id_item)
            self.table.setItem(i, 2, name_item)
            self.table.setItem(i, 3, result_item)
            self.table.setItem(i, 4, details_item)
            self.table.setItem(i, 5, time_item)

            self.task_row_map[(browser_id, task_name)] = i

        self.table.setUpdatesEnabled(True)

    def update_task_progress(self, completed_tasks_data):
        for browser_id, results in completed_tasks_data.items():
            for result in results:
                task_name = result['task_name']
                key = (browser_id, task_name)

                if key in self.task_row_map:
                    row = self.task_row_map[key]

                    # FIX: Simply update the text of the existing, non-editable item
                    result_text = "成功" if result['status'] == 'SUCCESS' else "失败"
                    self.table.item(row, 3).setText(result_text)
                    self.table.item(row, 4).setText(result['details'])
                    self.table.item(row, 5).setText(result['timestamp'])

                    del self.task_row_map[key]

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_column_widths()

    def _update_column_widths(self):
        table_width = self.table.viewport().width()
        if table_width <= 0: return
        self.table.setColumnWidth(0, int(table_width * 0.10))
        self.table.setColumnWidth(1, int(table_width * 0.15))
        self.table.setColumnWidth(2, int(table_width * 0.20))
        self.table.setColumnWidth(3, int(table_width * 0.10))
        self.table.setColumnWidth(4, int(table_width * 0.30))
        self.table.setColumnWidth(5, int(table_width * 0.15))

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._update_column_widths)


class ExecutionResultsTab(QWidget):
    """执行结果标签页，包含侧边栏和内容区域。"""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 1. 左侧边栏
        sidebar_items = ["任务总进度", "已完成的任务", "已失败的任务"]
        self.sidebar = StyledSidebar(sidebar_items, 220)
        self.sidebar.currentRowChanged.connect(self.on_sidebar_changed)
        main_layout.addWidget(self.sidebar)

        # 2. 右侧内容堆栈
        self.content_stack = QStackedWidget()

        # 创建并添加 "任务总进度" 视图
        self.total_progress_view = TotalProgressWidget()
        self.content_stack.addWidget(self.total_progress_view)

        # 创建并添加 "已完成的任务" 的占位符视图
        self.completed_view = QLabel("这里将显示所有已完成的任务")
        self.completed_view.setAlignment(Qt.AlignCenter)
        self.content_stack.addWidget(self.completed_view)

        # 创建并添加 "已失败的任务" 的占位符视图
        self.failed_view = QLabel("这里将显示所有已失败的任务")
        self.failed_view.setAlignment(Qt.AlignCenter)
        self.content_stack.addWidget(self.failed_view)

        main_layout.addWidget(self.content_stack)

    def on_sidebar_changed(self, index):
        self.content_stack.setCurrentIndex(index)

    def populate_initial_tasks(self, tasks_data):
        self.total_progress_view.populate_initial_tasks(tasks_data)

    def update_task_progress(self, completed_tasks_data):
        self.total_progress_view.update_task_progress(completed_tasks_data)

class MyToolApplication(QWidget):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        self.controller = app_controller
        self.loaded_browser_ids = [] # 创建“全局”变量
        self.init_ui()
        self.start_backend_initialization()

    def init_ui(self):
        self.setWindowTitle(f"{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
        self.setWindowIcon(QIcon(os.path.join(AppConfig.BASE_DIR, 'icon', 'app-icon.png')))
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(''' QWidget { background-color: white; font-family: 'Microsoft YaHei'; } QTabWidget::pane { border: none; background: white; } QTabBar::tab { background: #f0f0f0; color: #333; padding: 14px 36px; margin-right: 4px; border-top-left-radius: 12px; border-top-right-radius: 12px; font-size: 18px; font-weight: bold; min-width: 120px; max-width: 300px; } QTabBar::tab:selected { background: #0078d4; color: white; } QTabBar::tab:hover { background: #e0e0e0; } QTabBar::tab:selected:hover { background: #0078d4; } ''')
        main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget(); self.tab_widget.setStyleSheet("QTabWidget::pane { border: none; }")
        self.log_widget = LogWidget()
        self.home_tab = HomeTab()
        self.config_tab = ConfigTab(self) # 传递主窗口引用
        self.results_tab = ExecutionResultsTab()
        self.project_tab = ProjectTab(self) # 传递主窗口引用

        self.tab_widget.addTab(self.home_tab, "首页")
        self.tab_widget.addTab(self.config_tab, "配置")
        self.tab_widget.addTab(self.project_tab, "项目")
        self.tab_widget.addTab(self.results_tab, "执行结果") # 添加新标签页

        self.tab_widget.tabBarClicked.connect(self.on_tab_bar_clicked)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
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
            projects = self.init_thread.projects # 从线程获取项目
            self.project_tab.populate_projects(projects)
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
