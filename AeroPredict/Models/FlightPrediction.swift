//
//  FlightPrediction.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//
//
  //  FlightPrediction.swift
  //  AeroPredict
  //
  //  Created by Hafsa Konain on 4/2/26.
  //
import Foundation

enum RiskLevel: String, Codable {
    case low = "Low"
    case medium = "Medium"
    case high = "High"
}

struct FlightPrediction: Codable, Equatable {
    let flightNumber: String
    let origin: String
    let destination: String
    let delayProbability: Int
    let riskLevel: RiskLevel
    let factors: [String]
}
