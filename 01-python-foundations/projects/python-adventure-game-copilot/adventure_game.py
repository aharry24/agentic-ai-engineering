# adventure_game.py
# A text-based adventure game where the player explores a forest or a cave
# while searching for a legendary treasure. The player makes choices that
# lead to winning (finding the treasure), losing (a poor decision ends the
# quest), or restarting the game after an unsuccessful attempt.

import sys
import time


def slow_print(text, delay=0.02):
    """Print text with a small delay per character for a more immersive feel."""
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def get_choice(prompt, valid_choices):
    """Prompt the player until they enter one of the valid choices."""
    while True:
        choice = input(prompt).strip().lower()
        if choice in valid_choices:
            return choice
        print(f"Invalid choice. Please choose one of: {', '.join(valid_choices)}")


def forest_path(player_name):
    """
    Describes the forest scenario. The player must choose between
    following a river or climbing a tree. Each choice leads to a
    different outcome using an if-else structure.
    """
    slow_print(f"\n{player_name} steps into the dense, whispering forest.")
    slow_print("Sunlight barely reaches the ground, and you hear a river nearby "
                "as well as rustling in the branches above.")

    choice = get_choice(
        "\nDo you want to (follow) the river or (climb) a tree? ",
        ["follow", "climb"]
    )

    if choice == "follow":
        slow_print("\nYou follow the river and discover an old stone bridge.")
        slow_print("Crossing it, you find a hidden path marked with ancient symbols "
                    "leading toward a mysterious cave entrance.")
        return "win"
    else:
        slow_print("\nYou climb the tallest tree to get a better view.")
        slow_print("A branch snaps beneath you, and you fall hard onto the forest floor.")
        slow_print("Injured and disoriented, your journey ends here.")
        return "lose"


def cave_path(player_name):
    """
    Describes the cave scenario. The player must choose between lighting
    a torch or proceeding in the dark. Conditionals determine the outcome.
    """
    slow_print(f"\n{player_name} approaches the mouth of a dark, mysterious cave.")
    slow_print("A cold draft flows from within, and you can barely see a few feet ahead.")

    choice = get_choice(
        "\nDo you want to (light) a torch or (proceed) in the dark? ",
        ["light", "proceed"]
    )

    if choice == "light":
        slow_print("\nYou light a torch. The flickering flame reveals glittering "
                    "gemstones embedded in the walls, and a chest resting on a stone pedestal.")
        slow_print("You open the chest and find the legendary treasure!")
        return "win"
    else:
        slow_print("\nYou proceed in the dark, feeling your way along the cold walls.")
        slow_print("Without warning, the ground gives way beneath you and you tumble "
                    "into a hidden pit.")
        slow_print("Your adventure ends in the darkness.")
        return "lose"


def start_game():
    """
    Displays the game introduction, asks for the player's name, and lets
    the player choose an initial path (forest or cave). Returns the
    outcome of the chosen path so the main loop can decide what happens next.
    """
    slow_print("=" * 60)
    slow_print("       WELCOME TO THE LEGEND OF THE LOST TREASURE")
    slow_print("=" * 60)
    slow_print("\nLegend speaks of a treasure hidden deep in an ancient land, "
                "guarded by nature and shadow alike. Only the bravest explorers "
                "dare to seek it out.")

    player_name = input("\nWhat is your name, explorer? ").strip()
    if not player_name:
        player_name = "Explorer"

    slow_print(f"\nWelcome, {player_name}! Your quest for the treasure begins now.")

    path_choice = get_choice(
        "\nWill you explore the (forest) or enter the (cave)? ",
        ["forest", "cave"]
    )

    if path_choice == "forest":
        result = forest_path(player_name)
    else:
        result = cave_path(player_name)

    return player_name, result


def show_result(player_name, result):
    """Displays the outcome of the game based on the result of the chosen path."""
    slow_print("\n" + "-" * 60)
    if result == "win":
        slow_print(f"CONGRATULATIONS, {player_name}! You found the legendary treasure!")
        slow_print("Your name will be remembered in the annals of great explorers.")
    else:
        slow_print(f"GAME OVER, {player_name}. Your quest has ended in failure.")
        slow_print("Fortune did not favor you this time...")
    slow_print("-" * 60)


def main():
    """
    Runs the adventure game in a loop until the player chooses not to
    restart after completing (or failing) their journey.
    """
    playing = True
    while playing:
        player_name, result = start_game()
        show_result(player_name, result)

        restart_choice = get_choice(
            "\nWould you like to play again? (yes/no) ",
            ["yes", "no"]
        )
        if restart_choice == "no":
            slow_print("\nThank you for playing! Farewell, explorer.")
            playing = False


if __name__ == "__main__":
    main()
