from typing import Tuple, Dict

import kornia.losses
import torch

from .imips import ImipLoss


class FocalCCELoss(ImipLoss):

    def __init__(self, epsilon: float = 1e-4):
        super(FocalCCELoss, self).__init__()
        self._epsilon = torch.nn.Parameter(torch.tensor([epsilon]), requires_grad=False)
        self._focal_cce_module = kornia.losses.FocalLoss(1.0, 2.0, reduction="mean")

    @property
    def needs_correspondence_outputs(self) -> bool:
        return False

    def forward_with_log_data(self, maximizer_outputs: torch.Tensor, correspondence_outputs: torch.Tensor,
                              inlier_labels: torch.Tensor, outlier_labels: torch.Tensor) -> Tuple[
        torch.Tensor, Dict[str, torch.Tensor]]:
        # maximizer_outputs: BxCx1x1 where B == C
        # correspondence_outputs: BxCx1x1 where B == C
        # If h and w are not 1 w.r.t. maximizer_outputs and correspondence_outputs,
        # the center values will be extracted.

        assert (maximizer_outputs.shape[0] == maximizer_outputs.shape[1] ==
                correspondence_outputs.shape[0] == correspondence_outputs.shape[1])

        assert (maximizer_outputs.shape[2] == maximizer_outputs.shape[3] ==
                correspondence_outputs.shape[2] == correspondence_outputs.shape[3])

        if maximizer_outputs.shape[2] != 1:
            center_px = (maximizer_outputs.shape[2] - 1) // 2
            maximizer_outputs = maximizer_outputs[:, :, center_px, center_px]
            # correspondence_outputs = correspondence_outputs[:, :, center_px, center_px]

        maximizer_outputs = maximizer_outputs.squeeze()  # BxCx1x1 -> BxC

        # convert the label types so we can use torch.diag() on the labels
        if inlier_labels.dtype == torch.bool:
            inlier_labels = inlier_labels.to(torch.uint8)

        if outlier_labels.dtype == torch.bool:
            outlier_labels = outlier_labels.to(torch.uint8)

        inlier_maximizer_outputs = maximizer_outputs[inlier_labels, :]
        inlier_maximizer_channels = torch.arange(inlier_labels.shape[0], device=inlier_labels.device)[inlier_labels]
        if inlier_maximizer_channels.numel() == 0:
            loss = torch.zeros([1], requires_grad=True, device=maximizer_outputs.device)
        else:
            loss = self._focal_cce_module(inlier_maximizer_outputs, inlier_maximizer_channels)

        return loss, {
            "loss": loss.detach(),
        }