@echo off
REM Rust environment setup for Othello Coach
set RUST_HOME=%USERPROFILE%\.cargo
set PATH=%RUST_HOME%\bin;%PATH%
echo Rust environment loaded.
