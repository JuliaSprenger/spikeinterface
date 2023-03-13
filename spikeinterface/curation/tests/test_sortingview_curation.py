import pytest
from pathlib import Path
import os

import spikeinterface as si
from spikeinterface.extractors import read_mearec
from spikeinterface import set_global_tmp_folder
from spikeinterface.postprocessing import (compute_correlograms, compute_unit_locations,
                                           compute_template_similarity, compute_spike_amplitudes)
from spikeinterface.curation import apply_sortingview_curation

if hasattr(pytest, "global_test_folder"):
    cache_folder = pytest.global_test_folder / "curation"
else:
    cache_folder = Path("cache_folder") / "curation"


ON_GITHUB = bool(os.getenv('GITHUB_ACTIONS'))
KACHERY_CLOUD_SET = bool(os.getenv('KACHERY_CLOUD_CLIENT_ID')) and bool(os.getenv('KACHERY_CLOUD_PRIVATE_KEY'))


set_global_tmp_folder(cache_folder)

# this needs to be run only once
def generate_sortingview_curation_dataset():
    import spikeinterface.widgets as sw

    local_path = si.download_dataset(remote_path='mearec/mearec_test_10s.h5')
    recording, sorting = read_mearec(local_path)

    we = si.extract_waveforms(recording, sorting, folder=None, mode="memory")

    _ = compute_spike_amplitudes(we)
    _ = compute_correlograms(we)
    _ = compute_template_similarity(we)
    _ = compute_unit_locations(we)

    # plot_sorting_summary with curation
    w = sw.plot_sorting_summary(we, curation=True, backend="sortingview")


@pytest.mark.skipif(ON_GITHUB and not KACHERY_CLOUD_SET, reason="Kachery cloud secrets not available")
def test_sortingview_curation():
    local_path = si.download_dataset(remote_path='mearec/mearec_test_10s.h5')
    _, sorting = read_mearec(local_path)

    # curation_link: 
    # https://figurl.org/f?v=gs://figurl/spikesortingview-10&d=sha1://bd53f6b707f8121cadc901562a89b67aec81cc81&label=SpikeInterface%20-%20Sorting%20Summary

    # from curation.json
    json_file = "sv-sorting-curation.json"
    sorting_curated_json = apply_sortingview_curation(sorting, uri_or_json=json_file, verbose=True)
    print(f"From JSON: {sorting_curated_json}")

    assert len(sorting_curated_json.unit_ids) == 9
    assert "#8-#9" in sorting_curated_json.unit_ids
    assert "accept" in sorting_curated_json.get_property_keys()
    assert "mua" in sorting_curated_json.get_property_keys()
    assert "artifact" in sorting_curated_json.get_property_keys()

    sorting_curated_json_accepted = apply_sortingview_curation(sorting, uri_or_json=json_file, include_labels=["accept"])
    sorting_curated_json_mua = apply_sortingview_curation(sorting, uri_or_json=json_file, exclude_labels=["mua"])
    sorting_curated_json_mua1 = apply_sortingview_curation(sorting, uri_or_json=json_file,
                                                          exclude_labels=["artifact", "mua"])
    assert len(sorting_curated_json_accepted.unit_ids) == 3
    assert len(sorting_curated_json_mua.unit_ids) == 6
    assert len(sorting_curated_json_mua1.unit_ids) == 5

    # from GH
    # curated link: https://figurl.org/f?v=gs://figurl/spikesortingview-10&d=sha1://bd53f6b707f8121cadc901562a89b67aec81cc81&label=SpikeInterface%20-%20Sorting%20Summary&s={%22sortingCuration%22:%22gh://SpikeInterface/test-sv-sorting-curation/main/test/curation-test.json%22}
    gh_uri = "gh://SpikeInterface/test-sv-sorting-curation/main/test/curation-test.json"
    sorting_curated_gh = apply_sortingview_curation(sorting, uri_or_json=gh_uri, verbose=True)
    print(f"From GH: {sorting_curated_gh}")

    assert len(sorting_curated_gh.unit_ids) == 9
    assert "#8-#9" in sorting_curated_gh.unit_ids
    assert "accept" in sorting_curated_gh.get_property_keys()
    assert "mua" in sorting_curated_gh.get_property_keys()
    assert "artifact" in sorting_curated_gh.get_property_keys()

    sorting_curated_gh_accepted = apply_sortingview_curation(sorting, uri_or_json=gh_uri, include_labels=["accept"])
    sorting_curated_gh_mua = apply_sortingview_curation(sorting, uri_or_json=gh_uri, exclude_labels=["mua"])
    sorting_curated_gh_art_mua = apply_sortingview_curation(sorting, uri_or_json=gh_uri,
                                                            exclude_labels=["artifact", "mua"])
    assert len(sorting_curated_gh_accepted.unit_ids) == 3
    assert len(sorting_curated_gh_mua.unit_ids) == 6
    assert len(sorting_curated_gh_art_mua.unit_ids) == 5


if __name__ == "__main__":
    # generate_sortingview_curation_dataset()
    test_sortingview_curation()
