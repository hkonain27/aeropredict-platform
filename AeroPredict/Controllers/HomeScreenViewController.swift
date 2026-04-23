//
//  HomeViewController.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//

import UIKit

class HomeScreenViewController: UIViewController, UITableViewDataSource, UITableViewDelegate, SaveFlightDelegate, UITextFieldDelegate {
    
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
        navigationController?.navigationBar.prefersLargeTitles = true

                setupView()
                setupTextField()
                setupButton()
                setupErrorLabel()
                setupLoadingIndicator()
                setupTableView()

                recentSearches = StorageManager.shared.loadFlights()
                tableView.reloadData()
            }

    private func setupView() {
        view.backgroundColor = UIColor.systemGray6
        tableView.backgroundColor = .clear
    }

    private func setupTextField() {
        flightTextField.delegate = self
        flightTextField.placeholder = "Enter flight number"
        flightTextField.autocapitalizationType = .allCharacters
        flightTextField.autocorrectionType = .no
        flightTextField.clearButtonMode = .whileEditing
        flightTextField.returnKeyType = .done
        flightTextField.backgroundColor = .white
        flightTextField.layer.cornerRadius = 16
        flightTextField.layer.borderWidth = 1
        flightTextField.layer.borderColor = UIColor.systemGray5.cgColor
        flightTextField.layer.shadowColor = UIColor.black.cgColor
        flightTextField.layer.shadowOpacity = 0.06
        flightTextField.layer.shadowOffset = CGSize(width: 0, height: 3)
        flightTextField.layer.shadowRadius = 8
        flightTextField.clipsToBounds = false

        let leftPadding = UIView(frame: CGRect(x: 0, y: 0, width: 14, height: 44))
        flightTextField.leftView = leftPadding
        flightTextField.leftViewMode = .always
    }

    private func setupButton() {
        predictButton.setTitle("Predict Delay", for: .normal)
        predictButton.backgroundColor = .systemBlue
        predictButton.setTitleColor(.white, for: .normal)
        predictButton.layer.cornerRadius = 18
        predictButton.titleLabel?.font = UIFont.systemFont(ofSize: 20, weight: .bold)
        predictButton.layer.shadowColor = UIColor.systemBlue.cgColor
        predictButton.layer.shadowOpacity = 0.25
        predictButton.layer.shadowOffset = CGSize(width: 0, height: 8)
        predictButton.layer.shadowRadius = 14
        predictButton.clipsToBounds = false
    }

            private func setupErrorLabel() {
                errorLabel.isHidden = true
                errorLabel.textColor = .systemRed
                errorLabel.font = UIFont.systemFont(ofSize: 14, weight: .medium)
                errorLabel.numberOfLines = 0
            }

            private func setupLoadingIndicator() {
                loadingIndicator.hidesWhenStopped = true
                loadingIndicator.stopAnimating()
            }

    private func setupTableView() {
        tableView.dataSource = self
        tableView.delegate = self
        tableView.separatorStyle = .none
        tableView.rowHeight = 110
        tableView.showsVerticalScrollIndicator = false
        tableView.contentInset = UIEdgeInsets(top: 8, left: 0, bottom: 20, right: 0)
    }
    
    func tableView(_ tableView: UITableView, heightForRowAt indexPath: IndexPath) -> CGFloat {
        return 110
    }
    @IBAction func predictTapped(_ sender: UIButton) {
        runPrediction()
            }

            private func runPrediction() {
                view.endEditing(true)
                errorLabel.isHidden = true

                let input = flightTextField.text?
                    .trimmingCharacters(in: .whitespacesAndNewlines)
                    .uppercased() ?? ""

                guard !input.isEmpty else {
                    errorLabel.text = "Please enter a flight number."
                    errorLabel.isHidden = false
                    return
                }

                predictButton.isEnabled = false
                predictButton.alpha = 0.7
                loadingIndicator.startAnimating()

                FlightService.shared.fetchPrediction(for: input) { [weak self] result in
                    guard let self = self else { return }

                    self.loadingIndicator.stopAnimating()
                    self.predictButton.isEnabled = true
                    self.predictButton.alpha = 1.0

                    switch result {
                    case .success(let prediction):
                        self.currentPrediction = prediction

                        if !self.recentSearches.contains(where: { $0.flightNumber == prediction.flightNumber }) {
                            self.recentSearches.insert(prediction, at: 0)
                        }

                        self.tableView.reloadData()
                        StorageManager.shared.saveFlights(self.recentSearches)

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
                return recentSearches.count
            }

    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let flight = recentSearches[indexPath.row]
        let cell = tableView.dequeueReusableCell(withIdentifier: "RecentCell", for: indexPath)

        var content = UIListContentConfiguration.subtitleCell()
        content.text = "\(flight.flightNumber)   \(flight.origin) → \(flight.destination)"
        content.secondaryText = "Delay: \(flight.delayProbability)%   Risk: \(flight.riskLevel.rawValue)"
        content.textProperties.font = UIFont.systemFont(ofSize: 18, weight: .bold)
        content.secondaryTextProperties.font = UIFont.systemFont(ofSize: 16, weight: .semibold)

        switch flight.riskLevel {
        case .low:
            content.secondaryTextProperties.color = .systemGreen
        case .medium:
            content.secondaryTextProperties.color = .systemOrange
        case .high:
            content.secondaryTextProperties.color = .systemRed
        }

        cell.contentConfiguration = content
        cell.selectionStyle = .none
        cell.backgroundColor = .white
        cell.layer.cornerRadius = 22
        cell.layer.masksToBounds = false
        cell.layer.shadowColor = UIColor.black.cgColor
        cell.layer.shadowOpacity = 0.06
        cell.layer.shadowOffset = CGSize(width: 0, height: 6)
        cell.layer.shadowRadius = 12

        return cell
    }

            func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
                currentPrediction = recentSearches[indexPath.row]
                performSegue(withIdentifier: "showPrediction", sender: self)
            }

            func didSaveFlight(_ flight: FlightPrediction) {
                if !recentSearches.contains(where: { $0.flightNumber == flight.flightNumber }) {
                    recentSearches.insert(flight, at: 0)
                }
                tableView.reloadData()
                StorageManager.shared.saveFlights(recentSearches)
            }

            func textFieldShouldReturn(_ textField: UITextField) -> Bool {
                runPrediction()
                return true
            }
        }
