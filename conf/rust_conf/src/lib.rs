use std::fs;
use std::env;
use std::path::PathBuf;
use std::process::exit;
mod vehicle;

pub fn load_vehicle() -> vehicle::Vehicle{
    // open toml file
    let dir = env::var("CUAUV_SOFTWARE")
        .expect("CUAUV_SOTWARE environment variable not found");
    let vehicle = env::var("CUAUV_VEHICLE")
        .expect("CUAUV_VEHICLE environment variable not found");
    let toml_file: PathBuf = [
        dir,
        "conf/".to_string(),
        vehicle + ".toml"
    ].iter().collect();

    let contents = match fs::read_to_string(&toml_file) {
        Ok(val) => val,
        Err(_) => {
            eprintln!("Could not reach file {}", &toml_file.display());
            exit(1);
        }
    };
    
    let data: vehicle::Vehicle= match toml::from_str(&contents) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("{}", e);
            exit(1);
        }
    };

    data
}

