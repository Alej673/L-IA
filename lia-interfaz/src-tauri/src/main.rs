// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // NOTA: "app_lib" debe coincidir con el nombre de tu proyecto en Cargo.toml
    // Si tu proyecto se llama "lia", esto podría ser lia_lib::run();
    app_lib::run();
}