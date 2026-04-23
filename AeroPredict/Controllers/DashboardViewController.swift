//
//  DashboardViewController.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//
import UIKit

class DashboardViewController: UIViewController {

    @IBOutlet weak var trendsLabel: UILabel!
    @IBOutlet weak var airlinesLabel: UILabel!

    
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground


//        title = "Dashboard"
//
//        trendsLabel?.text = """
//        Delay Trends
//
//        Mon: 42%
//        Tue: 48%
//        Wed: 53%
//        Thu: 45%
//        Fri: 61%
//        """
//
//        airlinesLabel?.text = """
//        Top Delayed Airlines
//
//        1. American Airlines
//        2. Delta Airlines
//        3. United Airlines
//        4. Southwest Airlines
//        """
    }
}
