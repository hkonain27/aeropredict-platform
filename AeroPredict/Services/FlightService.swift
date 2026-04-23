//
//  FlightService.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//
import Foundation

final class FlightService {
    static let shared = FlightService()
    private init() {}

    func fetchPrediction(for flightNumber: String, completion: @escaping (Result<FlightPrediction, Error>) -> Void) {
        let trimmed = flightNumber.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()

        if trimmed.isEmpty || trimmed == "AA999" {
            completion(.failure(NSError(domain: "FlightError", code: 404, userInfo: [
                NSLocalizedDescriptionKey: "Flight not found"
            ])))
            return
        }

        guard let url = URL(string: "https://jsonplaceholder.typicode.com/posts/1") else {
            completion(.failure(NSError(domain: "BadURL", code: 400)))
            return
        }

        URLSession.shared.dataTask(with: url) { _, _, error in
            if let error = error {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
                return
            }

            let prediction = FlightPrediction(
                flightNumber: trimmed,
                origin: "CLT",
                destination: "JFK",
                delayProbability: 75,
                riskLevel: .high,
                factors: ["Weather", "Air Traffic", "Aircraft", "Historical"]
            )

            DispatchQueue.main.async {
                completion(.success(prediction))
            }
        }.resume()
    }
}
