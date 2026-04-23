//
//  ProfileViewController.swift
//  AeroPredict
//
//  Created by Hafsa Konain on 4/2/26.
//

import UIKit

class ProfileViewController: UIViewController {

    @IBOutlet weak var nameLabel: UILabel!
    @IBOutlet weak var emailLabel: UILabel!
    @IBOutlet weak var preferencesLabel: UILabel!
    @IBOutlet weak var settingsLabel: UILabel!

    override func viewDidLoad() {
        super.viewDidLoad()

        title = "Profile"
        nameLabel.text = "Hafsa Konain"
        emailLabel.text = "hkonain@charlotte.edu"
        preferencesLabel.text = "Preferences"
        settingsLabel.text = "Settings"
    }
}
