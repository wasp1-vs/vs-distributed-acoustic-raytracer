// PI brauchen wir, um zufällige Richtungen im Raum zu erzeugen.
use std::f32::consts::PI;

use glam::Vec3;

// Rng wird benötigt, um zufällige Strahlenrichtungen zu erzeugen.
use rand::RngExt;

// Rayon wird für parallele Berechnung genutzt.
use rayon::iter::{IntoParallelIterator, ParallelIterator};

// Deserialize brauchen wir, damit input_config.json in diese Struct geladen werden kann.
use serde::Deserialize;

// Importiert unser geometry-Modul.
use crate::geometry;

// Importiert Ray und Triangle aus geometry.rs.
use crate::geometry::{Ray, Triangle};


// Diese Config wird aus input_config.json gelesen.
// Früher waren speaker_position und mic_position Vec2.
// Jetzt sind sie Vec3, also [x, y, z].
#[derive(Deserialize)]
pub struct SimulationConfig {
    pub max_bounces: u32,
    pub min_pressure: f32,
    pub mic_radius: f32,
    pub mic_position: Vec3,
    pub rays_to_cast: u32,
    pub speaker_position: Vec3,
}


// Diese Funktion erzeugt einen zufälligen Startstrahl in 3D.
fn generate_initial_ray(config: &SimulationConfig) -> Ray {
    let mut rng = rand::rng();

    // theta ist der Winkel um die Z-Achse.
    let theta: f32 = rng.random_range(0.0..(2.0 * PI));

    // z ist die zufällige Höhe/Richtung nach oben oder unten.
    // Der Wert liegt zwischen -1 und 1.
    let z: f32 = rng.random_range(-1.0..1.0);

    // Aus z berechnen wir den Radius in der XY-Ebene.
    // Dadurch entsteht eine gleichmäßig verteilte Richtung auf einer Kugel.
    let r = (1.0_f32 - z * z).sqrt();

    // Aus theta, r und z bauen wir eine 3D-Richtung.
    let direction = Vec3::new(
        r * theta.cos(),
        r * theta.sin(),
        z,
    ).normalize();

    Ray {
        origin: config.speaker_position,
        direction,
    }
}


// Diese Funktion simuliert einen einzelnen Schallstrahl.
//
// Mini-Beispiel:
// Ein Sound-Pfeil fliegt los.
// Wenn er ein Dreieck trifft, prallt er ab.
// Dabei verliert er Energie.
// Wenn er am Mikrofon vorbeifliegt, speichern wir Delay + Pressure.
fn simulate_single_ray(
    initial_ray: Ray,
    triangles: &Vec<Triangle>,
    config: &SimulationConfig,
    ray_hits: &mut Vec<(f32, f32, Vec3)>
) {
    // Alten Inhalt im Buffer löschen, damit keine Daten vom letzten Ray übrig bleiben.
    ray_hits.clear();

    // Der aktuelle Ray startet als initialer Ray.
    let mut current_ray = initial_ray;

    // Gesamte Strecke, die dieser Ray schon geflogen ist.
    let mut total_distance = 0.0;

    // Startdruck/Energie des Rays.
    let mut current_pressure = 1.0;

    // Der Ray darf nur eine begrenzte Anzahl an Reflexionen machen.
    for _bounce in 0..config.max_bounces {

        // Prüft, ob der Ray ein Dreieck trifft.
        // Wenn ja: Wir bekommen einen reflektierten Ray zurück.
        if let Some((bounced_ray, absorption)) = cast_ray(&current_ray, triangles) {

            // Startpunkt des aktuellen Flugsegments.
            let start_point = current_ray.origin;

            // Endpunkt des Flugsegments, also Trefferpunkt am Dreieck.
            let end_point = bounced_ray.origin;

            // Prüfen, ob der Ray auf diesem Segment nahe am Mikrofon vorbeigeflogen ist.
            if geometry::check_mic_intersection(
                start_point,
                end_point,
                config.mic_position,
                config.mic_radius
            ) {

                // Richtung vom Mikrofon zum Treffpunkt
                let direction = (end_point - config.mic_position).normalize();

                // Entfernung vom Segmentstart zum Mikrofon.
                // Einfach gehalten wie im bisherigen Code.
                let distance_to_mic = start_point.distance(config.mic_position);

                // Gesamtdistanz bis zum Mikrofon-Treffer.
                let total_distance_at_hit = total_distance + distance_to_mic;

                // Kleine Schutzprüfung gegen Treffer direkt beim Startpunkt.
                if total_distance_at_hit > 0.001 {

                    // Delay = Strecke / Schallgeschwindigkeit.
                    // 343 m/s ist ungefähr Schallgeschwindigkeit in Luft.
                    ray_hits.push((total_distance_at_hit / 343.0, current_pressure, direction));
                }
            }

            // Die geflogene Strecke bis zum Dreieck wird zur Gesamtdistanz addiert.
            total_distance += start_point.distance(end_point);

            // Bei jeder Reflexion verliert der Ray Energie.
            current_pressure *= (1.0 - absorption).sqrt();

            // Wenn der Ray zu leise geworden ist, brechen wir ab.
            if current_pressure < config.min_pressure {
                break;
            }

            // Der reflektierte Ray wird zum neuen aktuellen Ray.
            current_ray = bounced_ray;

        } else {
            // Wenn kein Dreieck getroffen wurde, fliegt der Ray ins Leere.
            break;
        }
    }
}


// Single-Thread-Version der Simulation.
// Wird eher für Tests oder Vergleich benutzt.
pub fn run_simulation_single(
    config: &SimulationConfig,
    triangles: &Vec<Triangle>
) -> (Vec<f32>, Vec<f32>, Vec<Vec3>) {
    let mut delays_singular = Vec::with_capacity(100_000);
    let mut pressures_singular = Vec::with_capacity(100_000);
    let mut directions_singular = Vec::with_capacity(100_000);

    // Temporärer Buffer, damit nicht für jeden Ray neu Speicher erzeugt wird.
    let mut temp_ray_buffer = Vec::with_capacity(100);

    for _ in 0..config.rays_to_cast {
        let current_ray = generate_initial_ray(config);

        simulate_single_ray(
            current_ray,
            triangles,
            config,
            &mut temp_ray_buffer
        );

        for (delay, pressure, dir) in &temp_ray_buffer {
            delays_singular.push(*delay);
            pressures_singular.push(*pressure);
            directions_singular.push(*dir);
        }
    }

    (delays_singular, pressures_singular, directions_singular)
}


// Parallele Version der Simulation.
// Das ist die wichtige schnelle Version.
pub fn run_simulation_parallel(
    config: &SimulationConfig,
    triangles: &Vec<Triangle>
) -> (Vec<f32>, Vec<f32>, Vec<Vec3>) {
    println!("starting execution");

    let (delays_par, pressures_par, directions_par, _) = (0..config.rays_to_cast)
        .into_par_iter()
        .fold(
            || {
                let local_delays = Vec::with_capacity(100_000);
                let local_pressures = Vec::with_capacity(100_000);
                let local_directions = Vec::with_capacity(100_000);
                let temp_ray_buffer = Vec::with_capacity(100);

                (local_delays, local_pressures, local_directions, temp_ray_buffer)
            },
            |mut thread_buckets, _| {
                let fresh_ray = generate_initial_ray(config);

                simulate_single_ray(
                    fresh_ray,
                    triangles,
                    config,
                    &mut thread_buckets.3
                );

                for (delay, pressure, direction) in &thread_buckets.3 {
                    thread_buckets.0.push(*delay);
                    thread_buckets.1.push(*pressure);
                    thread_buckets.2.push(*direction);
                }

                thread_buckets.3.clear();

                thread_buckets
            }
        )
        .reduce(
            || (Vec::new(), Vec::new(), Vec::new(), Vec::new()),
            |mut a, mut b| {
                a.0.append(&mut b.0);
                a.1.append(&mut b.1);
                a.2.append(&mut b.2);
                a
            }
        );

    (delays_par, pressures_par, directions_par)
}


// Diese Funktion sucht das nächstgelegene Dreieck, das der Ray trifft.
fn cast_ray(
    ray: &Ray,
    triangles: &Vec<Triangle>
) -> Option<(Ray, f32)> {
    let mut closest_bounced_ray: Option<(Ray, f32)> = None;

    // Sehr große Startdistanz, damit jeder echte Treffer kleiner ist.
    let mut shortest_distance = f32::MAX;

    for triangle in triangles {
        if let Some(bounced_ray) = geometry::check_intersection(ray, triangle) {
            let distance = ray.origin.distance(bounced_ray.origin);

            if distance < shortest_distance {
                shortest_distance = distance;
                closest_bounced_ray = Some((bounced_ray, triangle.absorption));
            }
        }
    }

    closest_bounced_ray
}


// Diese Funktion simuliert einen Ray nur für die Visualisierung.
// Sie speichert nicht Delay/Pressure, sondern nur Punkte des Pfades.
pub fn simulate_single_ray_visualisation(
    initial_ray: Ray,
    triangles: &Vec<Triangle>,
    config: &SimulationConfig,
    path_buffer: &mut Vec<Vec3>
) {
    path_buffer.clear();

    // Startpunkt speichern.
    path_buffer.push(initial_ray.origin);

    let mut current_ray = initial_ray;
    let mut current_pressure = 1.0;

    for _bounce in 0..config.max_bounces {
        if let Some((bounced_ray, absorption)) = cast_ray(&current_ray, triangles) {

            // Trefferpunkt speichern.
            path_buffer.push(bounced_ray.origin);

            current_pressure *= 1.0 - absorption;

            if current_pressure < config.min_pressure {
                break;
            }

            current_ray = bounced_ray;

        } else {
            break;
        }
    }
}


// Mehrere Rays für Visualisierung simulieren.
pub fn run_simulation_visualizer(
    rays_to_trace: u32,
    config: &SimulationConfig,
    triangles: &Vec<Triangle>
) -> Vec<Vec<Vec3>> {
    let mut all_paths = Vec::with_capacity(rays_to_trace as usize);
    let mut temp_path = Vec::with_capacity(config.max_bounces as usize + 1);

    for _ in 0..rays_to_trace {
        let current_ray = generate_initial_ray(config);

        simulate_single_ray_visualisation(
            current_ray,
            triangles,
            config,
            &mut temp_path
        );

        all_paths.push(temp_path.clone());
    }

    all_paths
}