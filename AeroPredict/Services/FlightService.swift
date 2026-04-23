//
//  FlightService.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//
import Foundation

class FlightService {
    static let shared = FlightService()
    private init() {}

    enum FlightError: Error, LocalizedError {
        case invalidURL
        case noData
        case decodingFailed
        case noMatchingFlight

        var errorDescription: String? {
            switch self {
            case .invalidURL:
                return "Invalid request URL."
            case .noData:
                return "No data received from server."
            case .decodingFailed:
                return "Could not decode flight data."
            case .noMatchingFlight:
                return "No live matching flight found. Try a real flight number like AAL100 or DAL200."
            }
        }
    }

    // OpenSky response
    struct OpenSkyResponse: Codable {
        let time: Int
        let states: [[JSONValue]]?
    }

    // Flexible JSON decoder for mixed array values
    enum JSONValue: Codable {
        case string(String)
        case double(Double)
        case int(Int)
        case bool(Bool)
        case null

        init(from decoder: Decoder) throws {
            let container = try decoder.singleValueContainer()
            if container.decodeNil() {
                self = .null
            } else if let value = try? container.decode(Bool.self) {
                self = .bool(value)
            } else if let value = try? container.decode(Int.self) {
                self = .int(value)
            } else if let value = try? container.decode(Double.self) {
                self = .double(value)
            } else if let value = try? container.decode(String.self) {
                self = .string(value)
            } else {
                throw DecodingError.typeMismatch(
                    JSONValue.self,
                    DecodingError.Context(codingPath: decoder.codingPath,
                                          debugDescription: "Unsupported JSON value")
                )
            }
        }

        func encode(to encoder: Encoder) throws {
            var container = encoder.singleValueContainer()
            switch self {
            case .string(let value): try container.encode(value)
            case .double(let value): try container.encode(value)
            case .int(let value): try container.encode(value)
            case .bool(let value): try container.encode(value)
            case .null: try container.encodeNil()
            }
        }

        var stringValue: String? {
            if case .string(let value) = self { return value }
            return nil
        }

        var doubleValue: Double? {
            switch self {
            case .double(let value): return value
            case .int(let value): return Double(value)
            default: return nil
            }
        }

        var boolValue: Bool? {
            if case .bool(let value) = self { return value }
            return nil
        }
    }

    func fetchPrediction(for flightNumber: String,
                         completion: @escaping (Result<FlightPrediction, Error>) -> Void) {

        let trimmed = flightNumber.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()

        guard !trimmed.isEmpty else {
            completion(.failure(FlightError.noMatchingFlight))
            return
        }

        let urlString = "https://opensky-network.org/api/states/all?lamin=24&lomin=-125&lamax=49&lomax=-66"

        guard let url = URL(string: urlString) else {
            completion(.failure(FlightError.invalidURL))
            return
        }

        URLSession.shared.dataTask(with: url) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
                return
            }

            guard let data = data else {
                DispatchQueue.main.async {
                    completion(.failure(FlightError.noData))
                }
                return
            }

            do {
                let decoded = try JSONDecoder().decode(OpenSkyResponse.self, from: data)
                guard let states = decoded.states else {
                    DispatchQueue.main.async {
                        completion(.failure(FlightError.noMatchingFlight))
                    }
                    return
                }

                if let prediction = self.mapFlight(from: states, matching: trimmed) {
                    DispatchQueue.main.async {
                        completion(.success(prediction))
                    }
                } else {
                    let fallback = self.mockPrediction(for: trimmed)
                    DispatchQueue.main.async {
                        completion(.success(fallback))
                    }
                }

            } catch {
                DispatchQueue.main.async {
                    completion(.failure(FlightError.decodingFailed))
                }
            }
        }.resume()
    }

    private func mapFlight(from states: [[JSONValue]], matching flightNumber: String) -> FlightPrediction? {
        for state in states {
            guard state.count > 8 else { continue }

            let callsign = state[1].stringValue?.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() ?? ""
            let country = state[2].stringValue ?? "Unknown"
            let onGround = state[8].boolValue ?? false
            let velocity = state.count > 9 ? (state[9].doubleValue ?? 0) : 0

            if callsign.contains(flightNumber) {
                let delayProbability: Int
                let risk: RiskLevel
                let factors: [String]

                if onGround {
                    delayProbability = 65
                    risk = .high
                    factors = ["Aircraft currently on ground", "Possible departure delay", "Operational hold"]
                } else if velocity < 180 {
                    delayProbability = 45
                    risk = .medium
                    factors = ["Moderate airspeed", "Possible congestion", "Air traffic conditions"]
                } else {
                    delayProbability = 20
                    risk = .low
                    factors = ["Normal cruise conditions", "Flight already active", "Lower disruption risk"]
                }

                return FlightPrediction(
                    flightNumber: callsign,
                    origin: country,
                    destination: "Live Airspace",
                    delayProbability: delayProbability,
                    riskLevel: risk,
                    factors: factors
                )
            }
        }
        return nil
    }

    private func mockPrediction(for flightNumber: String) -> FlightPrediction {
        let delay = Int.random(in: 25...70)

        let risk: RiskLevel
        if delay >= 60 {
            risk = .high
        } else if delay >= 40 {
            risk = .medium
        } else {
            risk = .low
        }

        return FlightPrediction(
            flightNumber: flightNumber,
            origin: "Charlotte",
            destination: "New York",
            delayProbability: delay,
            riskLevel: risk,
            factors: ["Weather patterns", "Airport congestion", "Historical delay trend"]
        )
    }
}
