import argparse
import os

import numpy as np
import torch
from torch import nn
from torch.utils.tensorboard import SummaryWriter
from torch.utils.data import DataLoader

from data.Kaggle_FFHQ_Resized_256px import ffhq_utils


def set_seed(seed):
    """
    Function for setting the seed for reproducibility.
    """
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.determinstic = True
    torch.backends.cudnn.benchmark = False

def save_model(model, checkpoint_name):
    """
    Saves the model parameters to a checkpoint file.

    Args:
        model: nn.Module object representing the model architecture.
        checkpoint_name: Name of the checkpoint file.
    """
    # Check if the saved_model directory exists, if not create it
    if not os.path.exists("saved_models"):
        os.mkdir("saved_models")

    torch.save(model.state_dict(), os.path.join("saved_models", checkpoint_name))


def load_model(model, checkpoint_name):
    """
    Loads the model parameters from a checkpoint file.

    Args:
        model: nn.Module object representing the model architecture.
        checkpoint_name: Name of the checkpoint file.
    Returns:
        model: nn.Module object representing the model architecture.
    """
    device = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")
    model.load_state_dict(torch.load(os.path.join("saved_models", checkpoint_name), map_location=device))
    return model


def train_model(model, lr, batch_size, epochs, checkpoint_name, device, train_dataset, val_dataset):
    """
    Trains a given model architecture for the specified hyperparameters.

    Args:
        model: Model architecture to train.
        lr: Learning rate to use in the optimizer.
        batch_size: Batch size to train the model with.
        epochs: Number of epochs to train the model for.
        checkpoint_name: Filename to save the best model on validation to.
        device: Device to use for training.
        train_dataset: The training dataset.
        val_dataset: The validation dataset.
    Returns:
        model: Model that has performed best on the validation set.

    TODO:
    Implement the training of the model with the specified hyperparameters.
    Save the best model to disk so you can load it later.
    """
    #######################
    # PUT YOUR CODE HERE  #
    #######################
    assert epochs > 0, "To train the model the amount of epochs has to be higher than 1."

    # Make dataloaders from the datasets
    train_loader = DataLoader(train_dataset, batch_size=batch_size,
                              generator=torch.Generator().manual_seed(42))
    valid_loader = DataLoader(val_dataset, batch_size=batch_size,
                              generator=torch.Generator().manual_seed(42))

    # Initializing the optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # Define loss
    loss = nn.CrossEntropyLoss()

    # Placeholder for saving the best model.
    best_valid_accuracy = 0

    # Use tensorboard to visualize the training process.
    writer = SummaryWriter(log_dir='./tboard_logs')

    # Training loop with validation after each epoch. Save the best model, and remember to use the lr scheduler.
    for epoch in range(epochs):
        train_losses = []

        # Training loop
        for batch_num, batch in enumerate(train_loader):
            # Send data to device
            images, targets = batch
            images, targets = images.to(device), targets.to(device)

            # Send images through the model
            predictions = model(images)

            # Calculate loss
            batch_loss = loss(predictions, targets)
            train_losses.append(batch_loss.item())

            # Log the loss
            writer.add_scalar('Loss/train', batch_loss.item(), epoch * len(train_loader) + batch_num)

            if batch_num % 100 == 0 or batch_num == len(train_loader) - 1:
                print('\r',
                      f"Epoch: {epoch}: batch {batch_num + 1}/{len(train_loader)}"
                      f", running loss: {np.average(train_losses)}", end='')

            # Reset gradients
            optimizer.zero_grad()

            # Perform backward pass and optimization
            batch_loss.backward()
            optimizer.step()

        # Validation and train accuracy
        model.eval()
        with torch.no_grad():
            train_epoch_accuracy = evaluate_model(model, train_loader, device)
            valid_epoch_accuracy = evaluate_model(model, valid_loader, device)
            print(f", train accuracy: {train_epoch_accuracy}, validation accuracy: {valid_epoch_accuracy}")
            if valid_epoch_accuracy > best_valid_accuracy:
                save_model(model, checkpoint_name)
                best_valid_accuracy = valid_epoch_accuracy

            # Log the accuracy
            writer.add_scalar('Accuracy/train', train_epoch_accuracy, epoch)
            writer.add_scalar('Accuracy/validation', valid_epoch_accuracy, epoch)
        model.train()

    # Load best model and return it.
    model = load_model(model, checkpoint_name).to(device)

    #######################
    # END OF YOUR CODE    #
    #######################
    return model


def evaluate_model(model, data_loader, device):
    """
    Evaluates a trained model on a given dataset.

    Args:
        model: Model architecture to evaluate.
        data_loader: The data loader of the dataset to evaluate on.
        device: Device to use for training.
    Returns:
        accuracy: The accuracy on the dataset.

    TODO:
    Implement the evaluation of the model on the dataset.
    Remember to set the model in evaluation mode and back to training mode in the training loop.
    """
    #######################
    # PUT YOUR CODE HERE  #
    #######################
    correct_predictions = 0
    number_examples = 0
    for images, targets in data_loader:
        # Send data to device
        images, targets = images.to(device), targets.to(device)
        predictions = model(images)

        # Calculate number of correct predictions
        predicted_labels = torch.argmax(predictions, dim=1)
        correct_predictions += sum(predicted_labels == targets)
        number_examples += len(targets)

    accuracy = correct_predictions / number_examples

    #######################
    # END OF YOUR CODE    #
    #######################
    return accuracy


def test_model(model, batch_size, device, seed, test_dataset):
    """
    Tests a trained model on the test set with all corruption functions.

    Args:
        model: Model architecture to test.
        batch_size: Batch size to use in the test.
        device: Device to use for training.
        seed: The seed to set before testing to ensure a reproducible test.
        test_dataset: The test dataset to use.
    Returns:
        test_results: Dictionary containing an overview of the accuracies achieved on the different
                      corruption functions and the plain test set.

    TODO:
    Evaluate the model on the plain test set. Make use of the evaluate_model function.
    For each corruption function and severity, repeat the test.
    Summarize the results in a dictionary (the structure inside the dict is up to you.)
    """
    set_seed(seed)

    # Set model to evaluation mode
    model.eval()

    test_results = {}

    with torch.no_grad():
        test_loader = DataLoader(test_dataset, batch_size=batch_size,
                                 generator=torch.Generator().manual_seed(42))
        accuracy = evaluate_model(model, test_loader, device)
        test_results['accuracy'] = accuracy

        # Test accuracy
        print(f"Test accuracy: {accuracy.item():.4f}")

    # Set model back to train mode
    model.train()

    return test_results

def main(args: argparse.Namespace):
    """
    Main function for training a classifier.
    :param args: Arguments from the command line.
    """
    # Define device and seed
    device = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")
    set_seed(args.seed)

    dataset = None

    if args.dataset == "FFHQ-Aging":
        train_dataset, valid_dataset, test_dataset = ffhq_utils.get_train_valid_test_dataset("data/Kaggle_FFHQ_Resized_256px", "gender")
    else:
        raise NotImplementedError
    
    model = torch.hub.load('pytorch/vision:v0.10.0', 'mobilenet_v2', pretrained=True).to(device)

    # Check if model was already trained, if it was import it, if not train it
    if not os.path.exists(os.path.join("saved_models", args.checkpoint_name)):
        train_model(model, args.lr, args.batch_size, args.epochs, args.checkpoint_name, device, train_dataset,
                    valid_dataset)
    else:
        load_model(model, args.checkpoint_name).to(device)

    # Then test the model with all the defined corruption features
    # Return the results
    test_results = test_model(model, args.batch_size, device, args.seed, test_dataset)

    return test_results


if __name__ == "__main__":
    # Start argparse
    parser = argparse.ArgumentParser(description="Train a classifier")

    # Dataset
    parser.add_argument("--dataset", type=str, default="FFHQ-Aging", help="Dataset to train on")

    # Labels
    parser.add_argument("--labels", type=str, default="gender", help="Labels to train on")

    # Optimizer hyperparameters
    parser.add_argument('--lr', default=0.01, type=float,
                        help='Learning rate to use')
    parser.add_argument('--batch_size', default=128, type=int,
                        help='Minibatch size')

    # Other hyperparameters
    parser.add_argument('--epochs', default=50, type=int,
                        help='Max number of epochs')
    parser.add_argument('--seed', default=42, type=int,
                        help='Seed to use for reproducing results')
    parser.add_argument('--checkpoint_name', default="FFHQ-Gender.pth", type=str, help="Name of the model checkpoint")

    # Parse and pass to main
    parse_args = parser.parse_args()
    main(parse_args)
