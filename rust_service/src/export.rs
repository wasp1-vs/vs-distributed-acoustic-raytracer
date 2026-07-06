use std::fs::File;
use std::io::BufWriter;

use glam::Vec3;
use serde::Serialize;
use crate::simulation::SimulationConfig;

#[derive(Serialize)]
struct OutputMetadata {
    sample_rate: u32,
    rays_cast: u32,
    rays_received: u32,
    room_name: String,
    wall_material: String,
}

#[derive(Serialize)]
struct OutputHits {
    delays_seconds: Vec<f32>,
    pressures: Vec<f32>,
}

#[derive(Serialize)]
struct IrOutput {
    metadata: OutputMetadata,
    hits: OutputHits,
}

#[derive(Serialize)]
pub struct VisualizerOutput {
    pub speaker: Vec3,
    pub mic: Vec3,
    pub mic_radius: f32,
    pub rays: Vec<Vec<Vec3>>,
}

pub fn export_results(
    delays: Vec<f32>,
    pressure: Vec<f32>,
    config: &SimulationConfig
) {
    let final_data = IrOutput {
        metadata: OutputMetadata {
            sample_rate: 44100,
            rays_cast: config.rays_to_cast,
            rays_received: delays.len() as u32,
            room_name: String::from("MVP_Test_Room_3D"),
            wall_material: config.wall_material.clone().unwrap_or_else(|| String::from("concrete")),
        },
        hits: OutputHits {
            delays_seconds: delays,
            pressures: pressure,
        },
    };

    let file = File::create("ir_output.json")
        .expect("Unable to create file");

    let writer = BufWriter::new(file);

    serde_json::to_writer_pretty(writer, &final_data)
        .expect("Unable to write JSON");

    println!(
        "Simulation done! Wrote {} hits to ir_output.json",
        final_data.metadata.rays_received
    );
}


pub fn export_visualisation_data(
    paths: Vec<Vec<Vec3>>,
    config: &SimulationConfig,
) {
    let final_data = VisualizerOutput {
        speaker: config.speaker_position,
        mic: config.mic_position,
        mic_radius: config.mic_radius,
        rays: paths,
    };

    let file = File::create("visualisation_data.json")
        .expect("Unable to create file");

    let writer = BufWriter::new(file);

    serde_json::to_writer_pretty(writer, &final_data)
        .expect("Unable to write JSON");

    println!("Exported visualisation_data.json!");
}