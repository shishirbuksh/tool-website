use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rand::Rng;
use std::collections::VecDeque;

#[pyfunction]
fn train_and_predict(py: Python, prices: Vec<f64>, lookback: usize, epochs: usize, future_days: usize) -> PyResult<Vec<f64>> {
    // ── Input guards: reject degenerate / abusive parameters ──
    if lookback == 0 || future_days == 0 || epochs == 0 {
        return Err(PyValueError::new_err(
            "lookback, future_days and epochs must all be > 0",
        ));
    }
    if future_days > 365 {
        return Err(PyValueError::new_err("future_days must be <= 365"));
    }
    if epochs > 1000 {
        return Err(PyValueError::new_err("epochs must be <= 1000"));
    }
    if lookback > 500 {
        return Err(PyValueError::new_err("lookback must be <= 500"));
    }
    // Reject NaN / infinite prices — they would poison scaling and training.
    if prices.iter().any(|p| !p.is_finite()) {
        return Err(PyValueError::new_err(
            "prices must not contain NaN or infinite values",
        ));
    }
    let n = prices.len();
    if n <= lookback {
        return Ok(vec![0.0; future_days]);
    }
    
    // Scale data using min-max scaling (0 to 1)
    let mut min = f64::MAX;
    let mut max = f64::MIN;
    for &p in prices.iter() {
        if p < min { min = p; }
        if p > max { max = p; }
    }
    if max - min < 1e-6 {
        return Ok(vec![prices.last().copied().unwrap_or(0.0); future_days]);
    }
    
    let mut scaled = vec![0.0; n];
    for i in 0..n {
        scaled[i] = (prices[i] - min) / (max - min);
    }
    
    let mut x: Vec<Vec<f64>> = Vec::new();
    let mut y: Vec<f64> = Vec::new();
    
    for i in lookback..n {
        let mut seq = Vec::new();
        for j in 0..lookback {
            seq.push(scaled[i - lookback + j]);
        }
        x.push(seq);
        y.push(scaled[i]);
    }
    
    // MLP setup: Input size = lookback, Hidden = 50, Output = 1
    let input_size = lookback;
    let hidden_size = 50;
    
    // NOTE on RNG: rand::thread_rng() is intentionally non-seeded per call so
    // concurrent Python threads don't share deterministic state. If reproducible
    // training is needed, seed a per-call StdRng (e.g. from a `seed` argument).
    // ROUND-2: CPU-bound training releases the GIL via `py.allow_threads`
    // so async workers / other Python threads stay responsive while training.
    // (Callers do NOT need an extra `loop.run_in_executor` for this path.)
    let predictions = py.allow_threads(|| {
    let mut rng = rand::thread_rng();
    
    // Weights and biases
    let mut w1: Vec<Vec<f64>> = vec![vec![0.0; input_size]; hidden_size];
    let mut b1: Vec<f64> = vec![0.0; hidden_size];
    let mut w2: Vec<f64> = vec![0.0; hidden_size];
    let mut b2: f64 = 0.0;
    
    // Xavier-like initialization
    for i in 0..hidden_size {
        for j in 0..input_size {
            w1[i][j] = rng.gen_range(-0.5..0.5);
        }
        b1[i] = rng.gen_range(-0.5..0.5);
        w2[i] = rng.gen_range(-0.5..0.5);
    }
    
    let learning_rate = 0.01;
    
    fn relu(val: f64) -> f64 { if val > 0.0 { val } else { 0.0 } }
    
    // Pre-allocate working memory to avoid heap thrashing in the hot loops
    let mut hidden = vec![0.0; hidden_size];
    let mut d_w2 = vec![0.0; hidden_size];
    let mut d_hidden = vec![0.0; hidden_size];
    
    for _epoch in 0..epochs {
        for i in 0..x.len() {
            // Forward pass
            for j in 0..hidden_size {
                let mut sum = b1[j];
                for k in 0..input_size {
                    sum += w1[j][k] * x[i][k];
                }
                hidden[j] = relu(sum);
            }
            
            let mut output = b2;
            for j in 0..hidden_size {
                output += w2[j] * hidden[j];
            }
            // Sigmoid activation to bound predictions to [0, 1]
            output = 1.0 / (1.0 + (-output).exp());
            
            let err = output - y[i];
            
            // Backprop: MSE derivative * Sigmoid derivative
            let d_output = 2.0 * err * output * (1.0 - output);
            
            for j in 0..hidden_size {
                d_w2[j] = d_output * hidden[j];
            }
            let d_b2 = d_output;
            
            for j in 0..hidden_size {
                let d_relu = if hidden[j] > 0.0 { 1.0 } else { 0.0 };
                d_hidden[j] = d_output * w2[j] * d_relu;
            }
            
            // Updates
            for j in 0..hidden_size {
                w2[j] -= learning_rate * d_w2[j];
                for k in 0..input_size {
                     w1[j][k] -= learning_rate * d_hidden[j] * x[i][k];
                }
                b1[j] -= learning_rate * d_hidden[j];
            }
            b2 -= learning_rate * d_b2;
        }
    }
    
    // Predict future_days
    // Use a VecDeque as a sliding window (O(1) pop_front) instead of
    // `Vec::remove(0)` which is O(n) per step.
    let mut current_seq: VecDeque<f64> = VecDeque::from(scaled[n - lookback..].to_vec());
    let mut predictions = Vec::new();
    // Clamp outputs to a sane non-negative range so one divergent step can't
    // produce negative prices or explode to infinity. Upper bound is 10x the
    // observed max (or 10x last price if max <= 0).
    let clamp_hi = if max > 0.0 { max * 10.0 } else { prices.last().copied().unwrap_or(0.0) * 10.0 };
    let clamp_hi = if clamp_hi.is_finite() && clamp_hi > 0.0 {
        clamp_hi
    } else {
        f64::MAX / 2.0
    };
    
    for _ in 0..future_days {
        let mut hidden = vec![0.0; hidden_size];
        for j in 0..hidden_size {
            let mut sum = b1[j];
            for k in 0..input_size {
                sum += w1[j][k] * current_seq[k];
            }
            hidden[j] = relu(sum);
        }
        let mut output = b2;
        for j in 0..hidden_size {
            output += w2[j] * hidden[j];
        }
        output = 1.0 / (1.0 + (-output).exp());
        
        let mut res = output * (max - min) + min;
        // Clamp to [0, max*10] so predictions stay non-negative and bounded.
        if !res.is_finite() {
            // Fall back to last good prediction (or 0.0) instead of NaN/Inf.
            res = predictions.last().copied().unwrap_or(0.0);
            if !res.is_finite() {
                res = 0.0;
            }
            res = res.clamp(0.0, clamp_hi);
        } else {
            res = res.clamp(0.0, clamp_hi);
        }
        predictions.push(res);

        current_seq.pop_front();
        current_seq.push_back(output);
    }

        predictions
    });
    Ok(predictions)
}

#[pyfunction]
fn generate_pattern(py: Python, width: u32, height: u32, zoom: f64, c_re: f64, c_im: f64, max_iter: u32) -> PyResult<Vec<u8>> {
    // ── Guards: reject degenerate / abusive sizes ──
    if max_iter == 0 {
        return Err(PyValueError::new_err("max_iter must be > 0"));
    }
    if max_iter > 1000 {
        return Err(PyValueError::new_err("max_iter must be <= 1000"));
    }
    if width == 0 || height == 0 {
        return Err(PyValueError::new_err("width and height must be > 0"));
    }
    // Cap total pixels at 4M (~4 MB payload) to avoid OOM from huge requests.
    let pixels = (width as u64).checked_mul(height as u64).unwrap_or(u64::MAX);
    if pixels > 4_000_000 {
        return Err(PyValueError::new_err(
            "width*height must be <= 4,000,000 pixels",
        ));
    }
    if !zoom.is_finite() || zoom <= 0.0 {
        return Err(PyValueError::new_err("zoom must be a positive finite number"));
    }
    if !c_re.is_finite() || !c_im.is_finite() {
        return Err(PyValueError::new_err(
            "c_re and c_im must be finite numbers",
        ));
    }
    // ROUND-2: Julia-set loop is CPU-bound — release the GIL via
    // `py.allow_threads` so the async event loop stays responsive.
    let data = py.allow_threads(|| {
    let mut data = Vec::with_capacity((width as u64 * height as u64) as usize);

    for y in 0..height {
        for x in 0..width {
            let mut new_re = 1.5 * (x as f64 - width as f64 / 2.0) / (0.5 * zoom * width as f64);
            let mut new_im = (y as f64 - height as f64 / 2.0) / (0.5 * zoom * height as f64);
            
            let mut i = 0;
            while i < max_iter {
                let old_re = new_re;
                let old_im = new_im;
                new_re = old_re * old_re - old_im * old_im + c_re;
                new_im = 2.0 * old_re * old_im + c_im;
                if (new_re * new_re + new_im * new_im) > 4.0 {
                    break;
                }
                i += 1;
            }
            
            // Map iteration depth to structural pixel density payload
            let v = (i as f64 / max_iter as f64 * 255.0) as u8;
            data.push(v);
        }
    }
        data
    });
    Ok(data)
}

#[pymodule]
fn rust_predictor(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(train_and_predict, m)?)?;
    m.add_function(wrap_pyfunction!(generate_pattern, m)?)?;
    Ok(())
}
