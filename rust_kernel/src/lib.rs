use pyo3::prelude::*;
use pyo3::types::PyModule;

mod bitboards;
mod movegen;
mod stability;
mod solver;
mod popcount;

use movegen::*;
use stability::*;
use solver::*;

/// Legal move mask for a position
#[pyfunction]
fn legal_mask(b: u64, w: u64, stm: u8) -> PyResult<u64> {
    Ok(generate_legal_mask(b, w, stm))
}

/// Flip mask for a specific move
#[pyfunction]
fn flip_mask(b: u64, w: u64, stm: u8, sq: u8) -> PyResult<u64> {
    if sq >= 64 {
        return Ok(0);
    }
    Ok(generate_flip_mask(b, w, stm, sq))
}

/// Potential mobility calculation
#[pyfunction]
fn potential_mobility(b: u64, w: u64, stm: u8) -> PyResult<i16> {
    Ok(calculate_potential_mobility(b, w, stm))
}

/// Stability proxy calculation
#[pyfunction]
fn stability_proxy(b: u64, w: u64) -> PyResult<i16> {
    Ok(calculate_stability_proxy(b, w))
}

/// Parity regions analysis
#[pyfunction]
fn parity_regions(b: u64, w: u64) -> PyResult<Vec<(u64, u8)>> {
    Ok(calculate_parity_regions(b, w))
}

/// Exact solver for endgame positions
#[pyfunction]
fn exact_solver(b: u64, w: u64, stm: u8, empties: u8, tt_mb: u32) -> PyResult<i16> {
    if empties > 16 {
        return Ok(0); // Fall back to Python for >16 empties
    }
    Ok(solve_exact(b, w, stm, empties, tt_mb))
}

/// Python extension module: installs as `rust_kernel._rust_kernel`
#[pymodule]
fn rust_kernel(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(legal_mask, m)?)?;
    m.add_function(wrap_pyfunction!(flip_mask, m)?)?;
    m.add_function(wrap_pyfunction!(potential_mobility, m)?)?;
    m.add_function(wrap_pyfunction!(stability_proxy, m)?)?;
    m.add_function(wrap_pyfunction!(parity_regions, m)?)?;
    m.add_function(wrap_pyfunction!(exact_solver, m)?)?;
    Ok(())
}
