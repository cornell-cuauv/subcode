extern crate bindgen;

use std::env;
use std::path::PathBuf;

fn main() {
    let software;
    match env::var("software_path") {
        Ok(val) => software = val,
        Err(_e) => panic!("path software_path does not exist!")
    }

    let path: PathBuf = [software.to_string(), 
        "link-stage/".to_string()].iter().collect();
    let src_path: PathBuf = [software.to_string(), 
        "libshm/c".to_string()].iter().collect();
    let software_path: PathBuf = [software.to_string()].iter().collect();

    println!("cargo:rustc-link-search={}", path.display());
    println!("cargo:rustc-link-lib=shm");
    println!("cargo:rerun-if-changed=wrapper.h");

    // The bindgen::Builder is the main entry point
    // to bindgen, and lets you build up options for
    // the resulting bindings.
    let bindings = bindgen::Builder::default()
        // The input header we would like to generate
        // bindings for.
        .header("wrapper.h")
        .clang_arg(format!("-I{}", src_path.display()))
        .clang_arg(format!("-I{}", software_path.display()))
        // Tell cargo to invalidate the built crate whenever any of the
        // included header files changed.
        .parse_callbacks(Box::new(bindgen::CargoCallbacks))
        // Finish the builder and generate the bindings.
        .generate()
        // Unwrap the Result and panic on failure.
        .expect("Unable to generate bindings");

    // Write the bindings to the $OUT_DIR/bindings.rs file.
    let out_path = PathBuf::from(env::var("OUT_DIR").unwrap());
    bindings
        .write_to_file(out_path.join("bindings.rs"))
        .expect("Couldn't write bindings!");
}

