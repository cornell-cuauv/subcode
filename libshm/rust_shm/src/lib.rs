#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![allow(warnings)] //suppress warning about u128 being not FFI-safe
                    //shm is really safe:)
include!(concat!(env!("OUT_DIR"), "/bindings.rs"));
