use pyo3::prelude::*;
use rand::Rng;

#[pyfunction]
fn train_and_predict(prices: Vec<f64>, lookback: usize, epochs: usize, future_days: usize) -> PyResult<Vec<f64>> {
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
    
    for _epoch in 0..epochs {
        for i in 0..x.len() {
            let mut hidden = vec![0.0; hidden_size];
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
            
            let target = y[i];
            let err = output - target;
            
            let d_output = 2.0 * err; // MSE derivative wrt prediction
            
            let mut d_w2 = vec![0.0; hidden_size];
            for j in 0..hidden_size {
                d_w2[j] = d_output * hidden[j];
            }
            let d_b2 = d_output;
            
            let mut d_hidden = vec![0.0; hidden_size];
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
    let mut current_seq = scaled[n - lookback..].to_vec();
    let mut predictions = Vec::new();
    
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
        
        let res = output * (max - min) + min;
        predictions.push(res);
        
        current_seq.remove(0);
        current_seq.push(output);
    }
    
    Ok(predictions)
}

#[pymodule]
fn rust_predictor(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(train_and_predict, m)?)?;
    Ok(())
}
