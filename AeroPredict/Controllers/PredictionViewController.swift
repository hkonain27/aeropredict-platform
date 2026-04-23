//
//  PredictionViewController.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//
import UIKit

protocol SaveFlightDelegate: AnyObject {
    func didSaveFlight(_ flight: FlightPrediction)
}

class PredictionViewController: UIViewController {

    @IBOutlet weak var flightNumberLabel: UILabel!
    @IBOutlet weak var routeLabel: UILabel!
    @IBOutlet weak var delayLabel: UILabel!
    @IBOutlet weak var riskLabel: UILabel!
    @IBOutlet weak var factorsLabel: UILabel!
    @IBOutlet weak var saveButton: UIButton!

    var prediction: FlightPrediction?
    weak var delegate: SaveFlightDelegate?

    override func viewDidLoad() {
        super.viewDidLoad()

        title = "Prediction Details"

        guard let prediction = prediction else { return }

        flightNumberLabel.text = prediction.flightNumber
        routeLabel.text = "\(prediction.origin) → \(prediction.destination)"
        delayLabel.text = "\(prediction.delayProbability)%"
        riskLabel.text = prediction.riskLevel.rawValue
        factorsLabel.text = prediction.factors.joined(separator: ", ")
    }

    @IBAction func saveTapped(_ sender: UIButton) {
        guard let prediction = prediction else { return }

        var flights = StorageManager.shared.loadFlights()

        if !flights.contains(where: { $0.flightNumber == prediction.flightNumber }) {
            flights.append(prediction)
            StorageManager.shared.saveFlights(flights)
        }

        delegate?.didSaveFlight(prediction)
        saveButton.setTitle("Saved", for: .normal)
    }
}
