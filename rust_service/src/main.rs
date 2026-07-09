mod geometry;
mod simulation;
mod export;

use clap::Parser;

use geometry::Triangle;


use glam::Vec3;

use simulation::SimulationConfig;
use std::fs;
use std::time::Instant;


#[derive(Parser)]
#[command(name = "Acoustic Engine")]
#[command(about = "Multithreaded 3D acoustic raytracer", long_about = None)]
/// usage: cargo run --release -- --config-file input_config.json
struct Cli {
    /// Path to the JSON config file
    #[arg(short, long, default_value = "input_config.json")]
    config_file: String,
}


// Unser neuer Intersection-Algorithmus arbeitet mit Dreiecken.
// Eine echte Wand ist aber meistens rechteckig.
// Deshalb zerlegen wir ein Rechteck in zwei Dreiecke.
fn add_rect_as_two_triangles(
    triangles: &mut Vec<Triangle>,
    a: Vec3,
    b: Vec3,
    c: Vec3,
    d: Vec3,
    absorption: f32,
) {
    // Erstes Dreieck: a → b → c
    triangles.push(Triangle {
        v0: a,
        v1: b,
        v2: c,
        absorption,
    });

    // Zweites Dreieck: a → c → d
    triangles.push(Triangle {
        v0: a,
        v1: c,
        v2: d,
        absorption,
    });
}


fn main() {
    // CLI-Argumente einlesen.
    let cli = Cli::parse();

    println!("Reading config from: {}", cli.config_file);

    // input_config.json laden.
    let config_text = fs::read_to_string(&cli.config_file)
        .expect("Could not read config file");

    // JSON in SimulationConfig umwandeln.
    let test_config: SimulationConfig = serde_json::from_str(&config_text)
        .expect("Could not parse simulation config (Is the JSON formatted correctly?)");



    // Koordinatensystem:
    // x = links/rechts
    // y = vorne/hinten
    // z = Höhe
    //
    // Der Raum ist hier ein Würfel/Quader:
    // Breite: 10m
    // Tiefe: 10m
    // Höhe:  3m
    let width = 10.0;
    let depth = 10.0;
    let height = 10.0;

    // Absorption der Flächen.
    // 0.1 bedeutet: 10% Energieverlust pro Reflexion.
    let absorption = 0.2;

    // Liste aller Dreiecke im Raum.
    let mut room: Vec<Triangle> = Vec::new();


    // Boden
    add_rect_as_two_triangles(
        &mut room,
        Vec3::new(0.0, 0.0, 0.0),
        Vec3::new(width, 0.0, 0.0),
        Vec3::new(width, depth, 0.0),
        Vec3::new(0.0, depth, 0.0),
        absorption,
    );

    // Decke
    add_rect_as_two_triangles(
        &mut room,
        Vec3::new(0.0, 0.0, height),
        Vec3::new(width, 0.0, height),
        Vec3::new(width, depth, height),
        Vec3::new(0.0, depth, height),
        absorption,
    );

    // Wand vorne
    add_rect_as_two_triangles(
        &mut room,
        Vec3::new(0.0, 0.0, 0.0),
        Vec3::new(width, 0.0, 0.0),
        Vec3::new(width, 0.0, height),
        Vec3::new(0.0, 0.0, height),
        absorption,
    );

    // Wand hinten
    add_rect_as_two_triangles(
        &mut room,
        Vec3::new(0.0, depth, 0.0),
        Vec3::new(width, depth, 0.0),
        Vec3::new(width, depth, height),
        Vec3::new(0.0, depth, height),
        absorption,
    );

    // Wand links
    add_rect_as_two_triangles(
        &mut room,
        Vec3::new(0.0, 0.0, 0.0),
        Vec3::new(0.0, depth, 0.0),
        Vec3::new(0.0, depth, height),
        Vec3::new(0.0, 0.0, height),
        absorption,
    );

    // Wand rechts
    add_rect_as_two_triangles(
        &mut room,
        Vec3::new(width, 0.0, 0.0),
        Vec3::new(width, depth, 0.0),
        Vec3::new(width, depth, height),
        Vec3::new(width, 0.0, height),
        absorption,
    );


    println!("Starting 3D parallel simulation");

    let start_parallel = Instant::now();

 
    // Jetzt übergeben wir room als Vec<Triangle>.
    let (delays_par, pressures_par, directions_par) =
        simulation::run_simulation_parallel(&test_config, &room);

    let duration_parallel = start_parallel.elapsed().as_secs_f32();

    println!("Simulation run time: {} s", duration_parallel);

    // Ergebnisse als ir_output.json exportieren.
    export::export_results(delays_par, pressures_par, directions_par, &test_config);


    // Einige Rays für Visualisierung exportieren.
    let rays_to_visualize =
        simulation::run_simulation_visualizer(1, &test_config, &room);

    export::export_visualisation_data(rays_to_visualize, &test_config);
}