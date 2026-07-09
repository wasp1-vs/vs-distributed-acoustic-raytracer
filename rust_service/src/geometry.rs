use glam::Vec3;


// Ein Ray ist ein Schallstrahl.
// origin = Startpunkt des Strahls
// direction = Richtung, in die der Strahl fliegt
pub struct Ray {
    pub origin: Vec3,
    pub direction: Vec3,
}


// In 3D verwenden wir stattdessen Dreiecke.
// Ein Dreieck besteht aus drei Punkten: v0, v1 und v2.
//
// Warum Dreiecke?
// 3D-Flächen werden in Raytracing-Systemen fast immer aus Dreiecken aufgebaut,
// weil man mit Dreiecken sehr zuverlässig Schnittpunkte berechnen kann.
pub struct Triangle {
    pub v0: Vec3,
    pub v1: Vec3,
    pub v2: Vec3,
    pub absorption: f32,
}


// Diese Funktion prüft, ob ein Ray ein Dreieck trifft.
// -> Möller-Trumbore-Algorithmus.
//
// Der Algorithmus berechnet:
// - ob der Ray die Ebene des Dreiecks trifft
// - ob der Trefferpunkt wirklich innerhalb des Dreiecks liegt
// - wo genau der Trefferpunkt liegt
//
// Falls ein Treffer existiert, geben wir einen neuen reflektierten Ray zurück.
pub fn check_intersection(ray: &Ray, triangle: &Triangle) -> Option<Ray> {
    // Kleine Toleranz gegen Rundungsfehler bei float-Berechnungen.
    let epsilon = 1e-6;

    // Zwei Kanten des Dreiecks.
    // Diese spannen die Dreiecksfläche auf.
    let edge1 = triangle.v1 - triangle.v0;
    let edge2 = triangle.v2 - triangle.v0;

    // Kreuzprodukt zwischen Ray-Richtung und zweiter Dreieckskante.
    // Das wird im Möller-Trumbore-Algorithmus benutzt,
    // um später die baryzentrischen Koordinaten zu berechnen.
    let h = ray.direction.cross(edge2);

    // Wenn a ungefähr 0 ist, ist der Ray parallel zur Dreiecksfläche.
    // Dann gibt es keinen sinnvollen Schnittpunkt.
    let a = edge1.dot(h);

    if a.abs() < epsilon {
        return None;
    }

    // f ist der Kehrwert von a und wird für die weiteren Berechnungen genutzt.
    let f = 1.0 / a;

    // Vektor vom ersten Dreieckspunkt zum Ray-Ursprung.
    let s = ray.origin - triangle.v0;

    // u ist eine baryzentrische Koordinate.
    // Wenn u außerhalb von 0..1 liegt, ist der Treffer außerhalb des Dreiecks.
    let u = f * s.dot(h);

    if u < 0.0 || u > 1.0 {
        return None;
    }

    // q ist ein weiterer Hilfsvektor für die zweite baryzentrische Koordinate.
    let q = s.cross(edge1);

    // v ist die zweite baryzentrische Koordinate.
    let v = f * ray.direction.dot(q);

    // Wenn v außerhalb liegt oder u + v größer als 1 ist,
    // liegt der Trefferpunkt nicht im Dreieck.
    if v < 0.0 || u + v > 1.0 {
        return None;
    }

    // t beschreibt, wie weit der Ray fliegen muss, bis er das Dreieck trifft.
    let t = f * edge2.dot(q);

    // Wenn t zu klein oder negativ ist, liegt der Treffer hinter dem Ray
    // oder direkt am Startpunkt. Das ignorieren wir, um Selbsttreffer zu vermeiden.
    if t < 0.001 {
        return None;
    }

    // Der tatsächliche Trefferpunkt im 3D-Raum.
    let hit_point = ray.origin + ray.direction * t;

    // Die Normale des Dreiecks.
    // Diese steht senkrecht auf der Dreiecksfläche.
    // Sie wird gebraucht, um die Reflexion zu berechnen.
    let normal = edge1.cross(edge2).normalize();

    // Die neue Richtung nach dem Abprallen.
    // reflect(...) spiegelt die Richtung an der Dreiecksnormalen.
    let bounced_direction = ray.direction.reflect(normal).normalize();

    // Rückgabe des reflektierten Rays.
    // Der neue Ray startet am Trefferpunkt und fliegt in reflektierter Richtung weiter.
    Some(Ray {
        origin: hit_point,
        direction: bounced_direction,
    })
}


// Diese Funktion prüft, ob ein Ray-Segment nahe genug am Mikrofon vorbeifliegt.
//
// Wichtig:
// Wir prüfen nicht den unendlichen Ray, sondern nur das Stück zwischen:
// start = alter Ray-Punkt
// end   = Trefferpunkt an der Wand / am Dreieck
//
// Das Mikrofon wird hier als Kugel gedacht.
// Wenn der Abstand zwischen Segment und Mikrofon kleiner/gleich mic_radius ist,
// wird ein Treffer registriert.
pub fn check_mic_intersection(
    start: Vec3,
    end: Vec3,
    mic_center: Vec3,
    mic_radius: f32,
) -> bool {
    // Segment vom Startpunkt zum Endpunkt.
    let segment = end - start;

    // Länge des Segments im Quadrat.
    // Das ist schneller als direkt die echte Länge zu berechnen.
    let segment_length_sq = segment.length_squared();

    // Falls der Ray sich nicht bewegt hat, prüfen wir nur den Abstand vom Startpunkt.
    if segment_length_sq == 0.0 {
        return start.distance(mic_center) <= mic_radius;
    }

    // Vektor vom Startpunkt zum Mikrofon.
    let to_mic = mic_center - start;

    // Projektion des Mikrofons auf das Segment.
    let t = to_mic.dot(segment) / segment_length_sq;

    // clamp sorgt dafür, dass wir nur das echte Segment prüfen,
    // nicht die unendliche Verlängerung der Linie.
    let clamped_t = t.clamp(0.0, 1.0);

    // Der Punkt auf dem Segment, der dem Mikrofon am nächsten ist.
    let closest_point = start + segment * clamped_t;

    // Wenn dieser nächste Punkt innerhalb des Mikrofonradius liegt,
    // zählt das als Mikrofon-Treffer.
    closest_point.distance(mic_center) <= mic_radius
}