use glam::Vec3;

pub struct Ray {
    pub origin: Vec3,
    pub direction: Vec3,
}

pub struct Triangle {
    pub v0: Vec3,
    pub v1: Vec3,
    pub v2: Vec3,
    pub absorption: f32,
}


// Möller-Trumbore ray-triangle intersection.
// Returns the reflected ray at the hit point, or None if no intersection.
pub fn check_intersection(ray: &Ray, triangle: &Triangle) -> Option<Ray> {
    let epsilon = 1e-6;
    let edge1 = triangle.v1 - triangle.v0;
    let edge2 = triangle.v2 - triangle.v0;
    let h = ray.direction.cross(edge2);
    let a = edge1.dot(h);

    // Ray is parallel to the triangle surface
    if a.abs() < epsilon {
        return None;
    }

    let f = 1.0 / a;
    let s = ray.origin - triangle.v0;

    // Barycentric coordinate u – must be in [0, 1]
    let u = f * s.dot(h);
    if u < 0.0 || u > 1.0 {
        return None;
    }

    let q = s.cross(edge1);

    // Barycentric coordinate v – u + v must be ≤ 1
    let v = f * ray.direction.dot(q);
    if v < 0.0 || u + v > 1.0 {
        return None;
    }

    let t = f * edge2.dot(q);

    // Reject hits behind the ray or too close (avoids self-intersection)
    if t < 0.001 {
        return None;
    }

    let hit_point = ray.origin + ray.direction * t;
    let normal = edge1.cross(edge2).normalize();
    let bounced_direction = ray.direction.reflect(normal).normalize();

    Some(Ray {
        origin: hit_point,
        direction: bounced_direction,
    })
}


// Returns true if the ray segment (start → end) passes within mic_radius of mic_center.
// The mic is modeled as a sphere; only the finite segment is tested, not the infinite ray.
pub fn check_mic_intersection(
    start: Vec3,
    end: Vec3,
    mic_center: Vec3,
    mic_radius: f32,
) -> bool {
    let segment = end - start;
    let segment_length_sq = segment.length_squared();

    if segment_length_sq == 0.0 {
        return start.distance(mic_center) <= mic_radius;
    }

    let to_mic = mic_center - start;
    let t = to_mic.dot(segment) / segment_length_sq;

    // Clamp to the actual segment, not the infinite line
    let closest_point = start + segment * t.clamp(0.0, 1.0);
    closest_point.distance(mic_center) <= mic_radius
}