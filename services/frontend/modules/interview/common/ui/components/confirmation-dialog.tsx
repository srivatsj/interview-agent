"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { ConfirmationRequest } from "../views/use-confirmation";

interface ConfirmationDialogProps {
  open: boolean;
  request: ConfirmationRequest | null;
  onApprove: () => void;
  onDecline: () => void;
}

export function ConfirmationDialog({
  open,
  request,
  onApprove,
  onDecline,
}: ConfirmationDialogProps) {
  if (!request) return null;

  const { company, interview_type, price } = request;
  const isPaid = price > 0;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onDecline()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Payment Confirmation</DialogTitle>
          <DialogDescription>
            Please confirm your interview selection and payment.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 py-4">
          <div className="grid grid-cols-3 items-center gap-4">
            <span className="font-medium">Company:</span>
            <span className="col-span-2 capitalize">{company}</span>
          </div>

          <div className="grid grid-cols-3 items-center gap-4">
            <span className="font-medium">Interview Type:</span>
            <span className="col-span-2 capitalize">
              {interview_type.replace("_", " ")}
            </span>
          </div>

          {isPaid && (
            <div className="grid grid-cols-3 items-center gap-4">
              <span className="font-medium">Price:</span>
              <span className="col-span-2 text-lg font-bold text-green-600">
                ${price.toFixed(2)}
              </span>
            </div>
          )}

          {isPaid && (
            <div className="rounded-md bg-blue-50 p-3 text-sm text-blue-900">
              This interview uses a specialized AI agent and requires payment.
            </div>
          )}

          {!isPaid && (
            <div className="rounded-md bg-gray-50 p-3 text-sm text-gray-700">
              This is a free practice interview.
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onDecline}>
            Cancel
          </Button>
          <Button onClick={onApprove}>
            {isPaid ? `Pay $${price.toFixed(2)} & Start` : "Start Interview"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
