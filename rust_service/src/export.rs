// File wird benutzt, um JSON-Dateien zu erstellen.
use std::fs::File;

// BufWriter schreibt effizienter in Dateien.
use std::io::BufWriter;

use glam::Vec3;

// Serialize brauchen wir, damit Rust-Strukturen als JSON gespeichert werden können.
use serde::Serialize;

// SimulationConfig enthält die Daten aus input_config.json.
use crate::simulation::SimulationConfig;


// Metadaten für den IR-Export.
#[derive(Serialize)]
struct OutputMetadata {
    sample_rate: u32,
    rays_cast: u32,
    rays_received: u32,
    room_name: String,
}


// Die eigentlichen Akustik-Ergebnisse.
// delays_seconds = wann der Schall ankommt
// pressures = wie stark/leise der Schall ankommt
#[derive(Serialize)]
struct OutputHits {
    delays_seconds: Vec<f32>,
    pressures: Vec<f32>,
    directions: Vec<[f32; 3]>,
}


// Gesamtstruktur der ir_output.json.
#[derive(Serialize)]
struct IrOutput {
    metadata: OutputMetadata,
    hits: OutputHits,
}


// Datenstruktur für die Visualisierung.
// Jetzt alles mit Vec3, weil der Raum 3D ist.
#[derive(Serialize)]
pub struct VisualizerOutput {
    pub speaker: Vec3,
    pub mic: Vec3,
    pub mic_radius: f32,
    pub rays: Vec<Vec<Vec3>>,
}


// Exportiert die akustischen Ergebnisse in ir_output.json.
// Wichtig für die DSP-/Convolution-Pipeline.
pub fn export_results(
    delays: Vec<f32>,
    pressure: Vec<f32>,
    directions: Vec<Vec3>,
    config: &SimulationConfig
) {
    // Vec3 zu [f32; 3] konvertieren für JSON-Serialisierung
    let directions_array: Vec<[f32; 3]> = directions.iter()
        .map(|v| [v.x, v.y, v.z])
        .collect();

    let final_data = IrOutput {
        metadata: OutputMetadata {
            sample_rate: 44100,
            rays_cast: config.rays_to_cast,
            rays_received: delays.len() as u32,
            room_name: String::from("MVP_Test_Room_3D"),
        },
        hits: OutputHits {
            delays_seconds: delays,
            pressures: pressure,
            directions: directions_array,
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


// Exportiert die Ray-Pfade für Debugging/Visualisierung.
//
// Mini-Checks:
// - fliegen die Rays korrekt?
// - prallen sie an den Flächen ab?
// - sieht der Raum logisch aus?
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