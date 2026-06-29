mod sidecar;

use sidecar::{start_sidecar, SidecarManager};
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    AppHandle, Manager, RunEvent, State,
};

#[tauri::command]
fn get_api_base(manager: State<SidecarManager>) -> String {
    manager.api_base()
}

#[tauri::command]
fn get_server_origin(manager: State<SidecarManager>) -> String {
    manager.server_origin()
}

fn setup_tray(app: &AppHandle) -> tauri::Result<()> {
    let show_item = MenuItem::with_id(app, "show", "显示窗口", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&show_item, &quit_item])?;

    let icon = app.default_window_icon().expect("default window icon");

    TrayIconBuilder::new()
        .icon(icon.clone())
        .menu(&menu)
        .tooltip("Infinite Canvas")
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.unminimize();
                    let _ = window.set_focus();
                }
            }
            "quit" => {
                if let Some(manager) = app.try_state::<SidecarManager>() {
                    manager.kill();
                }
                app.exit(0);
            }
            _ => {}
        })
        .build(app)?;

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| -> Result<(), Box<dyn std::error::Error>> {
            let handle = app.handle().clone();
            let manager = start_sidecar(&handle).map_err(|error| {
                eprintln!("[sidecar] startup failed: {error}");
                error
            })?;

            let init_script = manager.initialization_script();
            app.manage(manager);

            if let Some(window) = app.get_webview_window("main") {
                window.eval(&init_script)?;
                let _ = window.show();
            }

            setup_tray(&handle)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_api_base, get_server_origin])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let RunEvent::Exit = event {
                if let Some(manager) = app_handle.try_state::<SidecarManager>() {
                    manager.kill();
                }
            }
        });
}
