# EMC--Traffic-Lights

This project simulates interconnected traffic junctions controlled by traffic lights and evaluates the impact of different timing strategies (fixed vs. adaptive) on traffic flow. It also includes a genetic algorithm to optimise signal timings. The simulation is built using [SimPy](https://simpy.readthedocs.io/) and provides visual animation of the network with the help of Matplotlib and NetworkX.

## Features

- **Fixed Timing Simulation:** Simulate traffic lights with predetermined timing values (from a CSV file or default values).
- **Actuated (Adaptive) Simulation:** Traffic lights that adjust their timings dynamically based on real-time traffic conditions.
- **Genetic Algorithm Optimisation:** Optimise the adaptive timing parameters to minimise wait times and improve overall network throughput.
- **Visual Animation:** Animated network visualisation with the option to save the output as an MP4 file (requires ffmpeg).

## Prerequisites

Ensure the following software is installed on your system:

- **Python 3.x** (Python 3.8 or higher is recommended)
- **pip** (Python package installer)
- **Git** (for cloning the repository, optional)
- **ffmpeg** – Required to generate video animations of the simulation:
  - **Using Chocolatey on Windows:**
    ```bash
    choco install ffmpeg
    ```
  - **Using Winget on Windows:**
    ```bash
    winget install ffmpeg
    ```

Additionally, install the required Python packages listed in `requirements.txt`:
- `simpy`
- `matplotlib`
- `networkx`

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/traffic-simulation.git
   cd traffic-simulation
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   Alternatively, install the packages manually:
   ```bash
   pip install simpy matplotlib networkx
   ```

3. **Install ffmpeg** using one of the commands provided above if it is not already installed.

## Usage

The project supports multiple modes:

- **sim:** Run the fixed simulation using the timing values loaded from the CSV file.
- **simdef:** Run the fixed simulation using default fixed timings (ignoring the CSV).
- **act:** Run the actuated (adaptive) simulation.
- **ga:** Run the genetic algorithm to optimise traffic light timings.

### Running the Simulation

Run the main entry point:
```bash
python main.py
```

At launch, you will be prompted to choose a simulation mode. For example:
- Enter `sim` to run the fixed timing simulation using CSV values.
- Enter `simdef` to run the fixed simulation using default timing values.
- Enter `act` for the actuated simulation.
- Enter `ga` for the genetic algorithm mode.

## Project Structure

- **main.py:**  
  Provides a command-line interface to choose between simulation modes and runs the selected simulation.

- **fixed_model.py:**  
  Implements the fixed timing simulation. It supports reading fixed signal timings from a CSV file or using default timings.

- **actuated_model.py:**  
  Implements the adaptive (actuated) simulation where signal timings adjust dynamically based on traffic conditions.

- **genetic_algorithm.py:**  
  Contains the genetic algorithm for optimising the traffic light timings.

- **quiet.py:**  
  Includes the core simulation classes for roads, junctions, traffic lights, and vehicles, along with kinematic equations and debug logging functionality.

- **display.py:**  
  Handles the visualisation of the traffic network using NetworkX and Matplotlib, including generating animations.

- **config.py:**  
  Contains configuration variables including grid dimensions, default timing values, and other simulation constants.

- **requirements.txt:**  
  Lists all Python packages required by the project.

## Contributing

Contributions are welcome! If you have ideas for improvements or encounter any issues, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.

## Acknowledgements

- [SimPy](https://simpy.readthedocs.io/) – for providing a robust discrete event simulation framework.
- [SUMO](https://www.eclipse.org/sumo/) – for inspiring traffic simulation methodologies.
- Special thanks to Dr Ed Horncastle, Dr Aeran Flemming and the team at Sprient Communications
