#!/bin/bash
# temporarily give software full access to dependencies so that cargo may work its magic
chown -R software /dependencies/
runuser -l software -c 'source /home/software/.cargo/env && 
    cargo fetch --manifest-path /dependencies/software_stack/Cargo.toml'
chown -R root /dependencies/ 
