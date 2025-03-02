import pytest
import numpy as np

import scipy.signal

from spikeinterface import download_dataset, BaseSorting
from spikeinterface.extractors import MEArecRecordingExtractor

from spikeinterface.sortingcomponents.peak_detection import detect_peaks
from spikeinterface.sortingcomponents.peak_pipeline import run_peak_pipeline, PipelineNode, ExtractDenseWaveforms, ExtractSparseWaveforms



class AmplitudeExtractionNode(PipelineNode):
    def __init__(self, recording, return_ouput=True, param0=5.5):
        PipelineNode.__init__(self, recording, return_ouput=return_ouput)
        self.param0 = param0
        self._dtype = np.dtype([('abs_amplitude', recording.get_dtype())])

    def get_dtype(self):
        return self._dtype
    
    def compute(self, traces, peaks):
        amps = np.zeros(peaks.size, dtype=self._dtype)
        amps['abs_amplitude'] = np.abs(peaks['amplitude'])
        return amps
    
    def get_trace_margin(self):
        return 5

class WaveformDenoiser(PipelineNode):
    # waveform smoother
    def __init__(self, recording, return_ouput=True, parents=None):
        PipelineNode.__init__(self, recording, return_ouput=return_ouput, parents=parents)

    def get_dtype(self):
        return np.dtype('float32')
    
    def compute(self, traces, peaks, waveforms):
        kernel = np.array([0.1, 0.8, 0.1])[np.newaxis, :, np.newaxis]
        denoised_waveforms = scipy.signal.fftconvolve(waveforms, kernel, axes=1, mode='same')
        return denoised_waveforms
    

class WaveformsRootMeanSquare(PipelineNode):
    def __init__(self, recording,  return_ouput=True, parents=None):
        PipelineNode.__init__(self, recording, return_ouput=return_ouput, parents=parents)

    def get_dtype(self):
        return np.dtype('float32')
    
    def compute(self, traces, peaks, waveforms):
        rms_by_channels = np.sum(waveforms ** 2, axis=1)
        return rms_by_channels


def test_run_peak_pipeline():

    repo = 'https://gin.g-node.org/NeuralEnsemble/ephy_testing_data'
    remote_path = 'mearec/mearec_test_10s.h5'
    local_path = download_dataset(
        repo=repo, remote_path=remote_path, local_folder=None)
    recording = MEArecRecordingExtractor(local_path)

    
    job_kwargs = dict(chunk_duration='0.5s', n_jobs=2, progress_bar=False)
    
    peaks = detect_peaks(recording, method='locally_exclusive',
                         peak_sign='neg', detect_threshold=5, exclude_sweep_ms=0.1,
                         **job_kwargs)
    
    # one step only : squeeze output
    nodes = [
        AmplitudeExtractionNode(recording, param0=6.6),
    ]
    step_one = run_peak_pipeline(recording, peaks, nodes, job_kwargs, squeeze_output=True)
    assert np.allclose(np.abs(peaks['amplitude']), step_one['abs_amplitude'])
    
    # 3 nodes two have outputs
    ms_before = 0.5
    ms_after = 1.0
    extract_waveforms = ExtractDenseWaveforms(recording, ms_before=ms_before, ms_after=ms_after, return_ouput=False)
    waveform_denoiser = WaveformDenoiser(recording, parents=[extract_waveforms], return_ouput=False)
    amplitue_extraction = AmplitudeExtractionNode(recording, param0=6.6, return_ouput=True)
    waveforms_rms = WaveformsRootMeanSquare(recording, parents=[extract_waveforms], return_ouput=True)
    denoised_waveforms_rms = WaveformsRootMeanSquare(recording, parents=[waveform_denoiser], return_ouput=True)
    
    nodes = [
        extract_waveforms,
        waveform_denoiser,
        amplitue_extraction,
        waveforms_rms,
        denoised_waveforms_rms,
    ]
    
        
    output = run_peak_pipeline(recording, peaks, nodes, job_kwargs)
    amplitudes, waveforms_rms, denoised_waveforms_rms = output
    assert np.allclose(np.abs(peaks['amplitude']), amplitudes['abs_amplitude'])
    
    num_peaks = peaks.shape[0]
    num_channels = recording.get_num_channels()
    assert waveforms_rms.shape[0] == num_peaks
    assert waveforms_rms.shape[1] == num_channels

    assert waveforms_rms.shape[0] == num_peaks
    assert waveforms_rms.shape[1] == num_channels
    
    # Test pickle mechanism
    for node in nodes:
        import pickle
        pickled_node = pickle.dumps(node)
        unpickled_node = pickle.loads(pickled_node)

if __name__ == '__main__':
    test_run_peak_pipeline()

