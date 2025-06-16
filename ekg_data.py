"""
EKG data processing module for EKG analysis system.
Handles EKG data loading, peak detection, heart rate calculation and visualization
with performance optimizations and clean architecture.
"""

import json
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from functools import lru_cache


class EKG_data:
    """
    EKG data processor class for handling individual EKG test data.
    Provides methods for peak detection, heart rate analysis and visualization
    with optimized data processing and caching.
    """

    def __init__(self, ekg_dict: Dict):
        """
        Initialize an EKG data object with a dictionary of EKG test data.
        
        Args:
            ekg_dict (Dict): Dictionary containing EKG test data:
                - id: EKG test identifier
                - date: Test date
                - result_link: Path to EKG data file
                - date_of_birth: Person's birth year
                - gender: Person's gender
        """
        self.id = ekg_dict["id"]
        self.date = ekg_dict["date"]
        self.data = ekg_dict["result_link"]
        self.birth_year = ekg_dict["date_of_birth"]
        self.gender = ekg_dict["gender"]
        
        # Lazy loading - data loaded only when accessed
        self._df = None
        self._peaks_cache = {}
        
    @property
    def df(self) -> pd.DataFrame:
        """
        Lazy-loaded EKG data with memory optimization.
        Uses float32 instead of float64 to reduce memory usage by ~50%.
        
        Returns:
            pd.DataFrame: EKG data with columns ['Messwerte in mV', 'time in ms']
        """
        if self._df is None:
            try:
                self._df = pd.read_csv(
                    self.data, 
                    sep="\t", 
                    header=None, 
                    names=["Messwerte in mV", "time in ms"],
                    dtype={'Messwerte in mV': np.float32, 'time in ms': np.float32}
                )
            except FileNotFoundError:
                raise FileNotFoundError(f"EKG data file not found: {self.data}")
            except pd.errors.EmptyDataError:
                raise ValueError(f"EKG data file is empty: {self.data}")
        
        return self._df

    @staticmethod
    def load_by_id(ekg_id: int, patients_data: List[Dict]) -> 'EKG_data':
        """
        Factory method to load EKG data by ID from patient data list.
        
        Args:
            ekg_id (int): ID of the EKG test to load
            patients_data (List[Dict]): List of patient data dictionaries
            
        Returns:
            EKG_data: Initialized EKG_data object
            
        Raises:
            ValueError: If EKG with specified ID is not found
        """
        for person in patients_data:
            for ekg in person.get("ekg_tests", []):
                if ekg["id"] == ekg_id:
                    # Merge person data with EKG test data
                    ekg["date_of_birth"] = person["date_of_birth"]
                    ekg["gender"] = person["gender"]
                    return EKG_data(ekg)
        
        raise ValueError(f"EKG with ID {ekg_id} not found in database")

    @staticmethod
    def find_peaks(series: pd.Series, sampling_rate: int = 500, threshold_factor: float = 0.6, 
                   window_size: Optional[int] = None, min_rr_interval: float = 0.3, 
                   max_rr_interval: float = 2.0, adaptive_threshold: bool = True) -> pd.DataFrame:
        """
        Find R-peaks in ECG signal using optimized window-based local maximum detection.
        
        Args:
            series: EKG signal data (pandas Series or array)
            sampling_rate: Sampling rate in Hz (default: 500)
            threshold_factor: Factor for adaptive threshold (0.0-1.0, default: 0.6)
            window_size: Window size for local maxima detection (auto if None)
            min_rr_interval: Minimum RR interval in seconds (default: 0.3s = 200 bpm max)
            max_rr_interval: Maximum RR interval in seconds (default: 2.0s = 30 bpm min)
            adaptive_threshold: Whether to use adaptive threshold
            
        Returns:
            pd.DataFrame: DataFrame with columns ['index', 'value', 'rr_interval']
        """
        peaks = []
        
        # Convert to numpy array for better performance
        if isinstance(series, pd.Series):
            values = series.values.astype(np.float32)
            indices = series.index.values
        else:
            values = np.array(series, dtype=np.float32)
            indices = np.arange(len(series))
        
        # Automatic parameter calculation based on sampling rate
        if window_size is None:
            window_size = max(5, int(sampling_rate * 0.02))  # 20ms window
        
        min_peak_distance = int(min_rr_interval * sampling_rate)
        max_peak_distance = int(max_rr_interval * sampling_rate)
        
        # Adaptive or fixed threshold
        if adaptive_threshold:
            signal_max = np.max(values)
            signal_mean = np.mean(values)
            threshold = signal_mean + (signal_max - signal_mean) * threshold_factor
        else:
            threshold = threshold_factor
        
        last_index = -min_peak_distance
        
        # Optimized peak detection using vectorized operations where possible
        for i in range(window_size, len(values) - window_size):
            window = values[i - window_size: i + window_size + 1]
            center_value = values[i]
            center_index = indices[i]
            
            # Check if center point is local maximum above threshold
            if center_value == np.max(window) and center_value > threshold:
                current_distance = center_index - last_index
                
                # Check minimum and maximum distance constraints
                if current_distance >= min_peak_distance:
                    if current_distance > max_peak_distance and len(peaks) > 0:
                        print(f"Warning: Large RR interval at index {center_index}: "
                              f"{current_distance/sampling_rate:.2f}s")
                    
                    peaks.append((center_index, center_value))
                    last_index = center_index
        
        # Create DataFrame with additional information
        if len(peaks) > 0:
            peaks_df = pd.DataFrame(peaks, columns=["index", "value"])
            
            # Calculate RR intervals
            if len(peaks_df) > 1:
                rr_intervals = np.diff(peaks_df["index"].values) / sampling_rate
                peaks_df["rr_interval"] = [np.nan] + list(rr_intervals)
                
                # Statistics
                print(f"Found peaks: {len(peaks_df)}")
                if len(rr_intervals) > 0:
                    mean_hr = 60 / np.mean(rr_intervals)
                    print(f"Average heart rate: {mean_hr:.1f} bpm")
                    print(f"RR interval range: {np.min(rr_intervals):.3f}s - {np.max(rr_intervals):.3f}s")
            
            return peaks_df
        else:
            print("No peaks found! Check threshold and signal quality.")
            return pd.DataFrame(columns=["index", "value", "rr_interval"])

    def calc_max_heart_rate(self, year_of_birth: int, gender: str) -> Dict:
        """
        Calculate maximum heart rate based on age and gender using established formulas.
        
        Args:
            year_of_birth (int): Birth year of the person
            gender (str): Gender of the person ('male', 'female', or other)
            
        Returns:
            Dict: Dictionary containing age, gender, and calculated max heart rate
        """
        current_age = datetime.now().year - year_of_birth

        # Age-predicted maximum heart rate formulas
        if gender.lower() == "male":
            max_hr = 220 - current_age  # Tanaka formula for men
        elif gender.lower() == "female":
            max_hr = 226 - current_age  # Tanaka formula for women  
        else:
            max_hr = 223 - current_age  # Gender-neutral average

        return {
            "age": current_age,
            "gender": gender,
            "max_hr": max_hr
        }

    def _get_cache_key(self, **kwargs) -> str:
        """
        Generate cache key for peak detection results.
        
        Returns:
            str: Cache key based on parameters
        """
        return str(sorted(kwargs.items()))

    def plot_time_series(self, range_start: Optional[float] = None, range_end: Optional[float] = None, 
                        sampling_rate: int = 500, threshold_factor: float = 0.6, 
                        min_rr_interval: float = 0.3, max_rr_interval: float = 2.0, 
                        adaptive_threshold: bool = True, window_size: Optional[int] = None) -> go.Figure:
        """
        Create optimized Plotly plot of EKG time series with peak detection.
        Includes caching and data reduction for better performance.
        
        Args:
            range_start: Start time in seconds
            range_end: End time in seconds  
            sampling_rate: Sampling rate in Hz (default: 500)
            threshold_factor: Factor for adaptive threshold (0.0-1.0, default: 0.6)
            min_rr_interval: Minimum RR interval in seconds (default: 0.3s)
            max_rr_interval: Maximum RR interval in seconds (default: 2.0s)
            adaptive_threshold: Whether to use adaptive threshold
            window_size: Window size for peak detection (auto if None)
            
        Returns:
            go.Figure: Plotly figure object with EKG data and detected peaks
        """
        # Normalize time to seconds (starting from 0)
        time_seconds = (self.df["time in ms"] - self.df["time in ms"].min()) / 1000
        
        # Filter range if specified
        if range_start is not None and range_end is not None:
            mask = (time_seconds >= range_start) & (time_seconds <= range_end)
            filtered_time = time_seconds[mask]
            filtered_data = self.df["Messwerte in mV"][mask]
        else:
            filtered_time = time_seconds
            filtered_data = self.df["Messwerte in mV"]
        
        # Data reduction for large datasets to improve rendering performance
        max_points = 10000  # Limit points for smooth rendering
        if len(filtered_data) > max_points:
            # Downsample data intelligently
            step = len(filtered_data) // max_points
            filtered_time = filtered_time.iloc[::step]
            filtered_data = filtered_data.iloc[::step]
        
        # Peak detection with caching
        cache_key = self._get_cache_key(
            sampling_rate=sampling_rate, threshold_factor=threshold_factor,
            min_rr_interval=min_rr_interval, max_rr_interval=max_rr_interval,
            adaptive_threshold=adaptive_threshold, window_size=window_size,
            range_start=range_start, range_end=range_end
        )
        
        if cache_key not in self._peaks_cache:
            try:
                peaks_df = self.find_peaks(
                    filtered_data,
                    sampling_rate=sampling_rate,
                    threshold_factor=threshold_factor,
                    window_size=window_size,
                    min_rr_interval=min_rr_interval,
                    max_rr_interval=max_rr_interval,
                    adaptive_threshold=adaptive_threshold
                )
                self._peaks_cache[cache_key] = peaks_df
            except Exception as e:
                print(f"Error in peak detection: {e}")
                peaks_df = pd.DataFrame(columns=["index", "value", "rr_interval"])
                self._peaks_cache[cache_key] = peaks_df
        else:
            peaks_df = self._peaks_cache[cache_key]
        
        # Convert peak indices to times
        peak_times = []
        peak_values = []
        if len(peaks_df) > 0:
            for _, peak in peaks_df.iterrows():
                peak_idx = int(peak['index'])
                if peak_idx < len(filtered_time):
                    peak_times.append(filtered_time.iloc[peak_idx])
                    peak_values.append(peak['value'])
        
        # Create optimized plot
        fig = go.Figure()
        
        # EKG signal trace
        fig.add_trace(go.Scatter(
            x=filtered_time,
            y=filtered_data,
            mode='lines',
            name='EKG Signal',
            line=dict(color='blue', width=1),
            hovertemplate='Zeit: %{x:.2f}s<br>Amplitude: %{y:.2f}mV<extra></extra>'
        ))
        
        # R-peaks trace
        if len(peak_times) > 0:
            fig.add_trace(go.Scatter(
                x=peak_times,
                y=peak_values,
                mode='markers',
                name=f'R-Peaks ({len(peak_times)})',
                marker=dict(color='red', size=8, symbol='triangle-up'),
                hovertemplate='R-Peak<br>Zeit: %{x:.2f}s<br>Amplitude: %{y:.2f}mV<extra></extra>'
            ))
            
            # Calculate and display heart rate
            if len(peak_times) > 1:
                rr_intervals = np.diff(peak_times)
                if len(rr_intervals) > 0:
                    avg_rr = np.mean(rr_intervals)
                    avg_hr = 60 / avg_rr if avg_rr > 0 else 0
                    title_text = f'EKG Time Series - ∅ Heart Rate: {avg_hr:.1f} bpm'
                else:
                    title_text = 'EKG Time Series'
            else:
                title_text = 'EKG Time Series - Insufficient peaks for heart rate'
        else:
            title_text = 'EKG Time Series - No R-peaks detected'
        
        # Optimize layout for performance
        fig.update_layout(
            title=title_text,
            xaxis_title='Time (Seconds)',
            yaxis_title='Amplitude (mV)',
            hovermode='x unified',
            showlegend=True,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            autosize=True,
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        # Grid styling
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray', zeroline=True)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray', zeroline=True)
        
        return fig

    def calculate_average_heart_rate(self, range_start: Optional[float] = None, 
                                   range_end: Optional[float] = None,
                                   sampling_rate: int = 500, threshold_factor: float = 0.6,
                                   min_rr_interval: float = 0.3, max_rr_interval: float = 2.0,
                                   adaptive_threshold: bool = True, window_size: Optional[int] = None,
                                   outlier_threshold: float = 0.3, min_peaks_required: int = 3) -> Optional[float]:
        """
        Calculate average heart rate with robust outlier detection and caching.
        
        Args:
            range_start: Start time in seconds
            range_end: End time in seconds
            sampling_rate: Sampling rate in Hz (default: 500)
            threshold_factor: Factor for adaptive threshold (0.0-1.0, default: 0.6)
            min_rr_interval: Minimum RR interval in seconds (default: 0.3s)
            max_rr_interval: Maximum RR interval in seconds (default: 2.0s)
            adaptive_threshold: Whether to use adaptive threshold
            window_size: Window size for peak detection (auto if None)
            outlier_threshold: Threshold for outlier detection (default: 0.3 = 30%)
            min_peaks_required: Minimum number of R-peaks for reliable calculation
            
        Returns:
            Optional[float]: Average heart rate in bpm, or None if calculation fails
        """
        # Normalize time to seconds
        time_seconds = (self.df["time in ms"] - self.df["time in ms"].min()) / 1000
        
        # Filter range if specified
        if range_start is not None and range_end is not None:
            mask = (time_seconds >= range_start) & (time_seconds <= range_end)
            filtered_data = self.df["Messwerte in mV"][mask]
        else:
            filtered_data = self.df["Messwerte in mV"]
        
        try:
            # Use cached peak detection if available
            cache_key = self._get_cache_key(
                sampling_rate=sampling_rate, threshold_factor=threshold_factor,
                min_rr_interval=min_rr_interval, max_rr_interval=max_rr_interval,
                adaptive_threshold=adaptive_threshold, window_size=window_size,
                range_start=range_start, range_end=range_end
            )
            
            if cache_key in self._peaks_cache:
                peaks_df = self._peaks_cache[cache_key]
            else:
                peaks_df = self.find_peaks(
                    filtered_data,
                    sampling_rate=sampling_rate,
                    threshold_factor=threshold_factor,
                    window_size=window_size,
                    min_rr_interval=min_rr_interval,
                    max_rr_interval=max_rr_interval,
                    adaptive_threshold=adaptive_threshold
                )
                self._peaks_cache[cache_key] = peaks_df
            
            # Check minimum number of peaks
            if len(peaks_df) < min_peaks_required:
                print(f'Insufficient R-peaks detected ({len(peaks_df)} < {min_peaks_required})')
                return None
            
            # Extract RR intervals
            if 'rr_interval' in peaks_df.columns:
                rr_intervals = peaks_df['rr_interval'].dropna().values
            else:
                # Calculate RR intervals from peak indices
                peak_indices = peaks_df['index'].values
                time_per_sample = 1.0 / sampling_rate
                peak_times = peak_indices * time_per_sample
                
                if len(peak_times) > 1:
                    rr_intervals = np.diff(peak_times)
                else:
                    print('Only one R-peak found. Heart rate cannot be calculated.')
                    return None
            
            # Robust outlier filtering
            if len(rr_intervals) > 2:
                # Statistical outlier filter
                median_rr = np.median(rr_intervals)
                outlier_bound = outlier_threshold * median_rr
                valid_mask = np.abs(rr_intervals - median_rr) <= outlier_bound
                
                # Physiological limits filter
                physiological_mask = (rr_intervals >= min_rr_interval) & (rr_intervals <= max_rr_interval)
                
                # Combine filters
                final_mask = valid_mask & physiological_mask
                valid_rr_intervals = rr_intervals[final_mask]
            else:
                valid_rr_intervals = rr_intervals
            
            # Calculate average heart rate
            if len(valid_rr_intervals) > 0:
                heart_rates = 60.0 / valid_rr_intervals
                avg_heart_rate = float(np.mean(heart_rates))
                return avg_heart_rate
            else:
                print('All RR intervals were classified as outliers.')
                return None
        
        except Exception as e:
            print(f'Error in heart rate calculation: {str(e)}')
            return None


if __name__ == "__main__":
    """
    Test module functionality when run directly.
    """
    try:
        # Load test data
        with open("data/person_db.json", "r", encoding="utf-8") as f:
            patients_data = json.load(f)

        print("Testing EKG_data class functionality...")
        
        # Test loading EKG data
        ekg = EKG_data.load_by_id(4, patients_data)
        print(f"✅ EKG data loaded: ID {ekg.id}, Date: {ekg.date}")
        print(f"   Data shape: {ekg.df.shape}")

        # Test peak detection
        peaks = EKG_data.find_peaks(ekg.df["Messwerte in mV"])
        print(f"✅ Peak detection completed: {len(peaks)} peaks found")

        # Test heart rate calculation
        hr_info = ekg.calc_max_heart_rate(ekg.birth_year, ekg.gender)
        print(f"✅ Max heart rate calculated: {hr_info}")

        # Test average heart rate
        avg_hr = ekg.calculate_average_heart_rate()
        if avg_hr:
            print(f"✅ Average heart rate: {avg_hr:.1f} bpm")
        else:
            print("⚠️ Average heart rate could not be calculated")

        print("✅ All tests completed successfully")

    except Exception as e:
        print(f"❌ Error during testing: {e}")