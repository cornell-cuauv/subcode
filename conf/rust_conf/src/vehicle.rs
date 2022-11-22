use nalgebra::{SVector, SMatrix};
use serde::{Deserialize, Deserializer};
//use serde_derive::Deserialize;

#[allow(non_snake_case)]
#[derive(Debug, serde_derive::Deserialize)]
pub struct DragPlane{
    #[serde(deserialize_with = "to_vector64f_3")]
    pub pos: SVector<f64, 3>,  
    #[serde(deserialize_with = "to_vector64f_3")]
    pub normal: SVector<f64, 3>, 
    pub cD: f64,
    pub area: f64,
}


#[derive(Debug, serde_derive::Deserialize)]
pub struct ThrusterVector{
    pub name: String,
    #[serde(alias = "type")] //type is a rust keyword ;-;
    pub motor_type: String,    
    #[serde(deserialize_with = "to_vector64f_3")]
    pub pos: SVector<f64, 3>,
    pub heading_pitch: [f64; 2], 
    pub reversed: bool,
}

#[derive(Debug, serde_derive::Deserialize)]
pub struct CameraBackward {
    #[serde(alias = "type")]
    pub camera_type: String,
    pub camera_name: String,
    pub id: i32,
    pub width: i32,
    pub height: i32,
    #[serde(deserialize_with = "to_vector64f_3")]
    pub position: SVector<f64, 3>,
    pub rotate180: bool,
    pub rotate90: bool,
    #[serde(deserialize_with = "to_vector64f_3")]
    pub orientation_hpr: SVector<f64, 3>,
    pub sensor_size_wh_mm: [f64; 2],
    pub focal_length_mm: f64,
}

#[derive(Debug, serde_derive::Deserialize)]
pub struct CameraForward{
    #[serde(alias = "type")]
    pub camera_type: String,
    pub camera_name: String,
    pub id: i32,
    pub width: i32,
    pub height: i32,
    #[serde(deserialize_with = "to_vector64f_3")]
    pub position: SVector<f64, 3>,
    #[serde(deserialize_with = "to_vector64f_3")]
    pub orientation_hpr: SVector<f64, 3>,
    pub sensor_size_wh_mm: [f64; 2],
    pub focal_length_mm: f64,
}

#[derive(Debug, serde_derive::Deserialize)]
pub struct CameraBundle {
    pub forward: CameraForward,
    pub downward: CameraBackward,
}

#[allow(non_snake_case)]
#[derive(Debug, serde_derive::Deserialize)]
pub struct Vehicle {
    #[serde(deserialize_with = "to_vector64f_3")]
    pub center_of_buoyancy: SVector<f64, 3>,
    pub buoyancy_force: f64,
    pub gravity_force: f64,
    pub sub_height: f64,
    #[serde(deserialize_with = "to_matrix64f_3x3")]
    pub I: SMatrix<f64, 3, 3>,
    #[serde(deserialize_with = "to_vector64f_3")]
    pub Ib: SVector<f64, 3>,
    #[serde(deserialize_with = "to_vector64f_4")]
    pub btom_rq: SVector<f64, 4>,
    pub drag_planes: Vec<DragPlane>,
    pub uncompensated_drag_planes: Vec<DragPlane>,
    #[serde(deserialize_with = "to_vector64f_6")]
    pub cwhe_axes: SVector<f64,6>,
    #[serde(deserialize_with = "to_vector64f_6")]
    pub thruster_minimums: SVector<f64, 6>,
    #[serde(deserialize_with = "to_vector64f_6")]
    pub thruster_maximums: SVector<f64, 6>,
    pub thrusters: Vec<ThrusterVector>,
    pub cameras: CameraBundle, 
}


// allow serde to unpack array into SVectors and SMatrices
fn to_vector64f_3<'de, D>(deserializer: D) -> Result<SVector<f64, 3>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: [f64; 3] = Deserialize::deserialize(deserializer)?;
    Ok(SVector::from(s))
}

fn to_vector64f_4<'de, D>(deserializer: D) -> Result<SVector<f64, 4>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: [f64; 4] = Deserialize::deserialize(deserializer)?;
    Ok(SVector::from(s))
}


fn to_vector64f_6<'de, D>(deserializer: D) -> Result<SVector<f64, 6>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: [f64; 6] = Deserialize::deserialize(deserializer)?;
    Ok(SVector::from(s))
}

fn to_matrix64f_3x3<'de, D>(deserializer: D) -> Result<SMatrix<f64, 3,3>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: [[f64; 3]; 3] = Deserialize::deserialize(deserializer)?;
    Ok(SMatrix::from(s))
}


