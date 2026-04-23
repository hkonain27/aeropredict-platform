//
//  HomeViewController.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//

import UIKit

class HomeViewController: UIViewController, UITableViewDataSource, UITableViewDelegate {

    @IBOutlet weak var flightTextField: UITextField!
    @IBOutlet weak var predictButton: UIButton!
    @IBOutlet weak var errorLabel: UILabel!
    @IBOutlet weak var tableView: UITableView!
    @IBOutlet weak var loadingIndicator: UIActivityIndicatorView!

    var recentSearches: [FlightPrediction] = []
    var currentPrediction: FlightPrediction?

    override func viewDidLoad() {
        super.viewDidLoad()

        title = "AeroPredict"
        errorLabel.isHidden = true
        loadingIndicator.hidesWhenStopped = true

        tableView.dataSource = self
        tableView.delegate = self

        recentSearches = StorageManager.shared.loadFlights()
    }

    @IBAction func predictTapped(_ sender: UIButton) {
        errorLabel.isHidden = true
        loadingIndicator.startAnimating()

        let input = flightTextField.text ?? ""

        FlightService.shared.fetchPrediction(for: input) { [weak self] result in
            guard let self = self else { return }

            self.loadingIndicator.stopAnimating()

            switch result {
            case .success(let prediction):
                self.currentPrediction = prediction

                if !self.recentSearches.contains(where: { $0.flightNumber == prediction.flightNumber }) {
                    self.recentSearches.insert(prediction, at: 0)
                }

                self.tableView.reloadData()
                self.performSegue(withIdentifier: "showPrediction", sender: self)

            case .failure(let error):
                self.errorLabel.text = error.localizedDescription
                self.errorLabel.isHidden = false
            }
        }
    }

    override func prepare(for segue: UIStoryboardSegue, sender: Any?) {
        if segue.identifier == "showPrediction",
           let destination = segue.destination as? PredictionViewController {
            destination.prediction = currentPrediction
            destination.delegate = self
        }
    }

    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        recentSearches.count
    }

    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {

        let flight = recentSearches[indexPath.row]
        let cell = tableView.dequeueReusableCell(withIdentifier: "RecentCell", for: indexPath)

        var content = cell.defaultContentConfiguration()
        content.text = "\(flight.flightNumber)   \(flight.origin) → \(flight.destination)"
        content.secondaryText = "Delay: \(flight.delayProbability)%   Risk: \(flight.riskLevel.rawValue)"
        cell.contentConfiguration = content

        return cell
    }
    func didSaveFlight(_ flight: FlightPrediction) {
        if !recentSearches.contains(where: { $0.flightNumber == flight.flightNumber }) {
            recentSearches.insert(flight, at: 0)
        }
        tableView.reloadData()
    }
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        currentPrediction = recentSearches[indexPath.row]
        performSegue(withIdentifier: "showPrediction", sender: self)
    }
}
