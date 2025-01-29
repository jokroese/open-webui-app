#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    use log::{error, info};
    use tauri::{Manager, RunEvent};
    use tauri_plugin_log::Builder as LogBuilder;
    use tauri_plugin_opener::init as OpenerInit;

    info!("🚀 Starting Open WebUI...");

    let app = tauri::Builder::default()
        // open files with the default system application
        .plugin(OpenerInit())
        // structured logging
        .plugin(LogBuilder::default().level(log::LevelFilter::Debug).build())
        .setup(|app| {
            info!("🔄 Running setup phase...");

            // show window when available
            if let Some(main_window) = app.get_webview_window("main") {
                if let Err(err) = main_window.show() {
                    error!("❌ Failed to show main window: {}", err);
                }
            } else {
                error!("❌ Could not retrieve main window.");
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Tauri application");

    app.run(move |_app_handle, event| match event {
        RunEvent::Reopen { .. } => {
            info!("🔄 App reopened!");
        }
        RunEvent::ExitRequested { api, .. } => {
            info!("🛑 Exit requested. Cleaning up...");
            api.prevent_exit();
        }
        _ => {}
    });
}
