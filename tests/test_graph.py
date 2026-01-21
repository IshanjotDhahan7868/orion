import yaml
from graph.dependency_graph import DependencyGraph
from graph.propagate import propagate_impact
from graph.asset_impact import aggregate_assets

def load_all():
    graph = DependencyGraph.from_yaml("config/graph.yaml")
    with open("config/assets.yaml") as f:
        assets = yaml.safe_load(f)
    with open("config/companies.yaml") as f:
        companies = yaml.safe_load(f)
    with open("config/technologies.yaml") as f:
        tech = yaml.safe_load(f)
    return graph, assets, companies, tech

def test_injection_mapping_has_tsm_and_advanced():
    graph, assets, companies, tech = load_all()
    assert "TSM" in companies
    assert "advanced_chips" in tech
    assert "Semiconductor_Manufacturing" in companies["TSM"]["nodes"]

def test_propagation_equipment_lifts_from_fab_event():
    graph, assets, companies, tech = load_all()
    start_nodes = set(companies["TSM"]["nodes"]) | set(tech["advanced_chips"]["nodes"])
    node_impacts, best_paths = propagate_impact(graph, list(start_nodes))
    assert node_impacts.get("Semiconductor_Equipment", 0) > 0

def test_assets_apply_type_weight_and_normalization():
    graph, assets, companies, tech = load_all()
    start_nodes = set(companies["TSM"]["nodes"]) | set(tech["advanced_chips"]["nodes"])
    ni, bp = propagate_impact(graph, list(start_nodes))
    scores, _ = aggregate_assets(ni, assets, bp)
    # ETFs shouldn't trivially dominate single names
    assert scores.get("ASML", 0) >= scores.get("SOXX", 0) * 0.5
