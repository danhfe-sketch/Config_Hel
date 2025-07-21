# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('ui', 'ui'),
    ],
    hiddenimports=[
        'services.theme_service',
        'services.i18n_service',
        'services.validation_service',
        'services.device_command_mapper',
        'services.serial_service',
        'services.config_service',
        'services.error_handling_service',
        'services.app_config_service',
        'ui.connection_frame',
        'ui.log_frame',
        'ui.parameters_frame',
        'ui.toolbar_frame',
        'ui.actions_frame',
        'ui.parameter_factory',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LT32Pro_Configurator_v1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to True temporarily for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/app_icon.ico'  # Using the newly created icon
)