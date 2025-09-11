import jiwer
import evaluate
import datasets

_CITATION = """@inproceedings{morris2004, author={...}}"""
_DESCRIPTION = """Character error rate (CER)."""
_KWARGS_DESCRIPTION = """Calculates CER."""

@evaluate.utils.file_utils.add_start_docstrings(_DESCRIPTION, _KWARGS_DESCRIPTION)
class CER(evaluate.Metric):
    def _info(self):
        return evaluate.MetricInfo(
            module_type="metric",
            description=_DESCRIPTION,
            citation=_CITATION,
            inputs_description=_KWARGS_DESCRIPTION,
            features=datasets.Features(
                {
                    "predictions": datasets.Value("string", id="sequence"),
                    "references": datasets.Value("string", id="sequence"),
                }
            ),
            reference_urls=["https://github.com/jitsi/jiwer"],
        )
    def _compute(self, predictions, references, concatenate_texts=False):
        if concatenate_texts:
            return jiwer.cer([" ".join(references)], [" ".join(predictions)])
        else:
            return jiwer.cer(references, predictions)