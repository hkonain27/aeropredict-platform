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
            navigationController?.navigationBar.prefersLargeTitles = false

            setupView()
            setupLabels()
            setupButton()
            updateUI()
        }

    private func setupView() {
        view.backgroundColor = UIColor.systemGray6
        view.clipsToBounds = false

    }

    private func setupLabels() {
        flightNumberLabel.font = UIFont.systemFont(ofSize: 34, weight: .bold)
        flightNumberLabel.textColor = .label

        routeLabel.font = UIFont.systemFont(ofSize: 20, weight: .semibold)
        routeLabel.textColor = .secondaryLabel
        routeLabel.numberOfLines = 0

        delayLabel.font = UIFont.systemFont(ofSize: 32, weight: .bold)
        delayLabel.textColor = .label

        riskLabel.font = UIFont.systemFont(ofSize: 18, weight: .bold)
        riskLabel.layer.cornerRadius = 14
        riskLabel.clipsToBounds = true
        riskLabel.textAlignment = .center

        factorsLabel.font = UIFont.systemFont(ofSize: 16, weight: .medium)
        factorsLabel.textColor = .secondaryLabel
        factorsLabel.numberOfLines = 0
    }

    private func setupButton() {
        saveButton.setTitle("Save Flight", for: .normal)
        saveButton.backgroundColor = .systemBlue
        saveButton.setTitleColor(.white, for: .normal)
        saveButton.layer.cornerRadius = 18
        saveButton.titleLabel?.font = UIFont.systemFont(ofSize: 18, weight: .bold)
        saveButton.layer.shadowColor = UIColor.systemBlue.cgColor
        saveButton.layer.shadowOpacity = 0.25
        saveButton.layer.shadowOffset = CGSize(width: 0, height: 8)
        saveButton.layer.shadowRadius = 14
        saveButton.clipsToBounds = false
    }
        private func updateUI() {
            guard let prediction = prediction else {
                flightNumberLabel.text = "No Prediction"
                            routeLabel.text = ""
                            delayLabel.text = "--"
                            riskLabel.text = ""
                            factorsLabel.text = "No data available."
                            saveButton.setTitle("Save Flight", for: .normal)
                            saveButton.backgroundColor = .systemGray
                            saveButton.setTitleColor(.white, for: .normal)
                            saveButton.isEnabled = false
                            saveButton.alpha = 0.6
                            return
                
            }

            flightNumberLabel.text = prediction.flightNumber
            routeLabel.text = "\(prediction.origin) → \(prediction.destination)"
            delayLabel.text = "\(prediction.delayProbability)%"
            riskLabel.text = "Risk: \(prediction.riskLevel.rawValue)"
            factorsLabel.text = "Factors: " + prediction.factors.joined(separator: ", ")

            switch prediction.riskLevel {
            case .low:
                riskLabel.backgroundColor = UIColor.systemGreen.withAlphaComponent(0.15)
                riskLabel.textColor = .systemGreen
            case .medium:
                riskLabel.backgroundColor = UIColor.systemOrange.withAlphaComponent(0.15)
                riskLabel.textColor = .systemOrange
            case .high:
                riskLabel.backgroundColor = UIColor.systemRed.withAlphaComponent(0.15)
                riskLabel.textColor = .systemRed
            }
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
               saveButton.backgroundColor = .systemGray
               saveButton.isEnabled = false
           }
       }
