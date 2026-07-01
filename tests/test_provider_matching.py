from uni_intel.ingestion.provider_matching import ProviderResolver, normalize_provider_name


def resolver() -> ProviderResolver:
    return ProviderResolver.from_records(
        providers=[
            ("university_of_melbourne", "The University of Melbourne"),
            ("university_of_technology_sydney", "University of Technology Sydney"),
            ("cquniversity", "CQUniversity"),
        ],
        aliases=[
            ("University of Melbourne", "university_of_melbourne", 1.0),
            ("University of Technology, Sydney", "university_of_technology_sydney", 1.0),
            ("Central Queensland University", "cquniversity", 1.0),
        ],
    )


def test_normalize_provider_name_removes_punctuation_and_leading_the() -> None:
    assert normalize_provider_name("The University of Technology, Sydney") == ("university of technology sydney")
    assert normalize_provider_name("University of New South Wales(1.03)") == ("university of new south wales")


def test_resolves_source_aliases() -> None:
    assert resolver().resolve("The University of Melbourne").provider_id == ("university_of_melbourne")
    assert resolver().resolve("University of Technology, Sydney").provider_id == ("university_of_technology_sydney")
    assert resolver().resolve("Central Queensland University").provider_id == "cquniversity"


def test_leaves_private_unseeded_provider_unmatched() -> None:
    assert resolver().resolve("Bond University") is None
