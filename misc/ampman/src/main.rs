use rust_shm;
fn main() {
    unsafe {rust_shm::shm_init();}
    loop {
        let heading = unsafe {rust_shm::shm_get_kalman_heading()};
        std::thread::sleep(std::time::Duration::from_millis(20));
        println!("heading: {}", heading);
    }
}
