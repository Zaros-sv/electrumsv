#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2013 ecdsa@github
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from functools import partial
import math
import random
import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QVBoxLayout, QGridLayout, QLabel, QCheckBox, QPushButton, QLineEdit, QWidget, QHBoxLayout,
    QSizePolicy
)

from electrumsv.i18n import _
from .util import (
    WindowModalDialog, OkButton, Buttons, CancelButton, icon_path, read_QIcon, ButtonsLineEdit
)


def check_password_strength(password):

    '''
    Check the strength of the password entered by the user and return back the same
    :param password: password entered by user in New Password
    :return: password strength Weak or Medium or Strong
    '''
    password = password
    n = math.log(len(set(password)))
    num = re.search("[0-9]", password) is not None and re.match("^[0-9]*$", password) is None
    caps = password != password.upper() and password != password.lower()
    extra = re.match("^[a-zA-Z0-9]*$", password) is None
    score = len(password)*( n + caps + num + extra)/20
    password_strength = {0:"Weak",1:"Medium",2:"Strong",3:"Very Strong"}
    return password_strength[min(3, int(score))]


PW_NEW, PW_CHANGE, PW_PASSPHRASE = range(0, 3)


class PasswordLineEdit(ButtonsLineEdit):
    """
    This only offers the keyboard button if it is not displayed in a dialog that originated
    from the keyboard button in an parental window.
    """

    def __init__(self, text='', keyboard_cb=None, keyboard=True):
        super().__init__(text)

        self.setEchoMode(QLineEdit.Password)

        if keyboard:
            if keyboard_cb is None:
                keyboard_cb = self.on_keyboard

            self.addButton("keyboard.png", keyboard_cb, "Virtual keyboard")

    def on_keyboard(self):
        d = PasswordDialog(self, keyboard=True, show_keyboard_toggle=False)
        text = d.run()
        if text is not None:
            self.setText(text)


class PasswordLayout(object):

    titles = [_("Enter Password"), _("Change Password"), _("Enter Passphrase")]

    def __init__(self, wallet, msg, kind, OK_button):
        self.wallet = wallet

        self.pw = PasswordLineEdit()
        self.new_pw = PasswordLineEdit()
        self.conf_pw = PasswordLineEdit()
        self.kind = kind
        self.OK_button = OK_button

        vbox = QVBoxLayout()
        label = QLabel(msg + "\n")
        label.setWordWrap(True)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(0, 150)
        grid.setColumnMinimumWidth(1, 100)
        grid.setColumnStretch(1,1)

        if kind == PW_PASSPHRASE:
            vbox.addWidget(label)
            msgs = [_('Passphrase:'), _('Confirm Passphrase:')]
        else:
            logo_grid = QGridLayout()
            logo_grid.setSpacing(8)
            logo_grid.setColumnMinimumWidth(0, 70)
            logo_grid.setColumnStretch(1,1)

            logo = QLabel()
            logo.setAlignment(Qt.AlignCenter)

            logo_grid.addWidget(logo,  0, 0)
            logo_grid.addWidget(label, 0, 1, 1, 2)
            vbox.addLayout(logo_grid)

            m1 = _('New Password:') if kind == PW_CHANGE else _('Password:')
            msgs = [m1, _('Confirm Password:')]
            if wallet and wallet.has_password():
                grid.addWidget(QLabel(_('Current Password:')), 0, 0)
                grid.addWidget(self.pw, 0, 1)
                lockfile = "lock.png"
            else:
                lockfile = "unlock.png"
            logo.setPixmap(QPixmap(icon_path(lockfile)).scaledToWidth(36))

        grid.addWidget(QLabel(msgs[0]), 1, 0)
        grid.addWidget(self.new_pw, 1, 1)

        grid.addWidget(QLabel(msgs[1]), 2, 0)
        grid.addWidget(self.conf_pw, 2, 1)
        vbox.addLayout(grid)

        # Password Strength Label
        if kind != PW_PASSPHRASE:
            self.pw_strength = QLabel()
            grid.addWidget(self.pw_strength, 3, 0, 1, 2)
            self.new_pw.textChanged.connect(self.pw_changed)

        self.encrypt_cb = QCheckBox(_('Encrypt wallet file'))
        self.encrypt_cb.setEnabled(False)
        grid.addWidget(self.encrypt_cb, 4, 0, 1, 2)
        self.encrypt_cb.setVisible(kind != PW_PASSPHRASE)

        def enable_OK():
            ok = self.new_pw.text() == self.conf_pw.text()
            OK_button.setEnabled(ok)
            self.encrypt_cb.setEnabled(ok and bool(self.new_pw.text()))
        self.new_pw.textChanged.connect(enable_OK)
        self.conf_pw.textChanged.connect(enable_OK)

        self.vbox = vbox

    def title(self):
        return self.titles[self.kind]

    def layout(self):
        return self.vbox

    def pw_changed(self):
        password = self.new_pw.text()
        if password:
            colors = {"Weak":"Red", "Medium":"Blue", "Strong":"Green",
                      "Very Strong":"Green"}
            strength = check_password_strength(password)
            label = (_("Password Strength") + ": " + "<font color="
                     + colors[strength] + ">" + strength + "</font>")
        else:
            label = ""
        self.pw_strength.setText(label)

    def old_password(self):
        if self.kind == PW_CHANGE:
            return self.pw.text() or None
        return None

    def new_password(self):
        pw = self.new_pw.text()
        # Empty passphrases are fine and returned empty.
        if pw == "" and self.kind != PW_PASSPHRASE:
            pw = None
        return pw


class ChangePasswordDialog(WindowModalDialog):

    def __init__(self, parent, wallet):
        WindowModalDialog.__init__(self, parent)
        is_encrypted = wallet.storage.is_encrypted()
        if not wallet.has_password():
            msg = _('Your wallet is not protected.')
            msg += ' ' + _('Use this dialog to add a password to your wallet.')
        else:
            if not is_encrypted:
                msg = _('Your bitcoins are password protected. However, your wallet file '
                        'is not encrypted.')
            else:
                msg = _('Your wallet is password protected and encrypted.')
            msg += ' ' + _('Use this dialog to change your password.')
        OK_button = OkButton(self)
        self.playout = PasswordLayout(wallet, msg, PW_CHANGE, OK_button)
        self.setWindowTitle(self.playout.title())
        self.setWindowIcon(read_QIcon("electrum-sv.png"))
        vbox = QVBoxLayout(self)
        vbox.addLayout(self.playout.layout())
        vbox.addStretch(1)
        vbox.addLayout(Buttons(CancelButton(self), OK_button))
        self.playout.encrypt_cb.setChecked(is_encrypted or not wallet.has_password())

    def run(self):
        if not self.exec_():
            return False, None, None, None
        return (True, self.playout.old_password(), self.playout.new_password(),
                self.playout.encrypt_cb.isChecked())


class PasswordDialog(WindowModalDialog):
    vkb_index = 0
    vkb = None

    pages = [
        ('Lower-case letters', 'text_lowercase.png', 'abcdefghijklmnopqrstuvwxyz_ '),
        ('Upper-case letters', 'text_uppercase.png', 'ABCDEFGHIJKLMNOPQRTSUVWXYZ_ '),
        ('Numbers and symbols', 'text_symbols.png', '1234567890!?.,;:/%&()[]{}+-$#*'),
    ]

    def __init__(self, parent=None, msg=None, keyboard=False, show_keyboard_toggle=True):
        msg = msg or _('Please enter your password')
        WindowModalDialog.__init__(self, parent, _("Enter Password"))
        self.pw = pw = PasswordLineEdit(
            keyboard_cb=self.toggle_keyboard,
            keyboard=show_keyboard_toggle)

        about_label = QLabel(msg)
        sp = QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        sp.setVerticalStretch(0)
        about_label.setSizePolicy(sp)

        vbox = QVBoxLayout()
        vbox.addWidget(about_label, Qt.AlignTop)

        edit_hbox = QHBoxLayout()
        edit_hbox.addWidget(QLabel(_('Password')))
        edit_hbox.addWidget(pw)
        vbox.addLayout(edit_hbox)

        vbox.addStretch(1)
        vbox.addLayout(Buttons(CancelButton(self), OkButton(self)), Qt.AlignBottom)
        self.setLayout(vbox)

        if keyboard:
            self.add_keyboard()

    def toggle_keyboard(self):
        if not self.remove_keyboard():
            self.add_keyboard()

    def add_keyboard(self):
        self.remove_keyboard()
        self.vkb = self.virtual_keyboard(self.vkb_index, self.pw)
        self.layout().insertLayout(2, self.vkb)

    def remove_keyboard(self):
        if self.vkb:
            self.layout().removeItem(self.vkb)
            self.vkb.setParent(None)
            QWidget().setLayout(self.vkb)
            self.vkb = None
            return True
        return False

    def virtual_keyboard(self, i, pw):
        this_page_index = i % len(self.pages)
        tooltip, icon_name, chars = self.pages[this_page_index]
        other_icon_indexes = list(range(len(self.pages)))
        random.shuffle(other_icon_indexes)

        candidates = list(chars)
        ordered_candidates = []

        while len(candidates):
            value = random.choice(candidates)
            candidates.remove(value)
            ordered_candidates.append(value)

        def add_target(t):
            return lambda: pw.setText(str(pw.text()) + t)

        grid = QGridLayout()
        grid.setSpacing(2)

        def create_grid_page_button(page_index, grid_index, page_data=None, disable=False):
            if page_data is None:
                page_data = self.pages[page_index]
            tooltip_text, icon_name, text = page_data
            l_button = self.add_grid_command_button(grid, grid_index, tooltip_text,
                icon_name, text, partial(self.change_keyboard_page, page_index))
            l_button.setDisabled(disable)
            return l_button

        page_data = "Regenerate page", "refresh_win10_16.png", None
        create_grid_page_button(this_page_index, 0, page_data)

        for i, page_index in enumerate(other_icon_indexes):
            disable = page_index == this_page_index
            l_button = create_grid_page_button(page_index, i+1, disable=disable)

        for i, value in enumerate(ordered_candidates):
            l_button = QPushButton()
            l_button.setText(value)
            l_button.clicked.connect(add_target(value))
            l_button.setFixedWidth(35)
            l_button.setFixedHeight(25)
            grid.addWidget(l_button, i // 6, 1 + (i % 6))

        return grid

    def change_keyboard_page(self, page_index):
        self.vkb_index = page_index
        self.add_keyboard()

    def add_grid_command_button(self, grid, row_index, tooltip_text, icon_name, text, click_cb):
        l_button = QPushButton()
        l_button.setIcon(read_QIcon(icon_name))
        l_button.setToolTip(tooltip_text)
        l_button.clicked.connect(click_cb)
        l_button.setFixedWidth(35)
        l_button.setFixedHeight(25)
        grid.addWidget(l_button, row_index, 0)
        return l_button

    def run(self):
        if not self.exec_():
            return None
        return self.pw.text()
