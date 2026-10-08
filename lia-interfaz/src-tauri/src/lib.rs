use tauri::{
    tray::{TrayIconBuilder, TrayIconEvent},
    Manager,
};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};
use std::str::FromStr;

// --- COMANDOS PARA EL EVENTO DE COLAPSO ---

#[tauri::command]
fn activar_modo_invasivo(app: tauri::AppHandle) {
    // Busca la segunda ventana y la hace visible
    if let Some(overlay) = app.get_webview_window("overlay_virus") {
        overlay.show().unwrap();
        overlay.set_focus().unwrap();
    }
}

#[tauri::command]
fn restaurar_ventana(app: tauri::AppHandle) {
    // Esconde los errores y L-IA sigue intacta en su ventana principal
    if let Some(overlay) = app.get_webview_window("overlay_virus") {
        overlay.hide().unwrap();
    }
}

// ------------------------------------------

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        // 0. Registrar los comandos para que React pueda llamarlos
        .invoke_handler(tauri::generate_handler![activar_modo_invasivo, restaurar_ventana])
        // Plugins existentes
        .plugin(tauri_plugin_log::Builder::default().build())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .setup(|app| {
            // 1. Crear el ícono de bandeja
            let icon = app.default_window_icon().cloned().unwrap();
            TrayIconBuilder::new()
                .icon(icon)
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click { .. } = event {
                        if let Some(window) = tray.app_handle().get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            // 2. Escuchar el atajo global de forma NATIVA (nunca se suspende)
            let ctrl_alt_j = Shortcut::from_str("ctrl+alt+j").unwrap();
            app.global_shortcut().on_shortcut(ctrl_alt_j, |app_handle, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    if let Some(window) = app_handle.get_webview_window("main") {
                        if window.is_visible().unwrap_or(false) {
                            let _ = window.hide();
                        } else {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                }
            })?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}