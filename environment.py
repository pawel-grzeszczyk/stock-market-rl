import numpy as np
from enum import Enum


class PositionType(Enum):
    LONG = 1
    HOLD = 0
    SHORT = -1


class TradingEnvironment:
    """
    A simulation of a trading environment..

    This class models the behavior of a trading environment, allowing an agent to
    perform actions such as opening new positions, buying more shares, selling shares, or holding.

    Attributes:
    - data (pandas.DataFrame): Historical price data [Timestamp, Open, High, Low, Close, Volume].
    - initial_balance (float): Initial balance for the portfolio.

    Methods:
    - reset(): Reset the trading environment to its initial state.
    - step(action, volume): Perform a trading step based on the given action and volume.
    - get_action_position_outcome(action_position): Get the corresponding outcome function for a given action and position type.
    - open_new_position(action, volume, current_price): Open a new position in the trading environment.
    - buy_more(action, volume, current_price): Buy more shares for an existing position.
    - sell(action, volume, current_price): Sell shares in the trading environment.
    - hold(action, volume, current_price): Hold the current position without any transaction.
    - update_portfolio_value(current_price): Update the portfolio value based on the current position.
    - print_status(): Print the current state, open position, balance, and portfolio value.
    """

    def __init__(self, data, initial_balance, transaction_fee):
        """
        Initialize the trading environment.

        Parameters:
        - data (pandas.DataFrame): Historical price data [Timestamp, Open, High, Low, Close, Volume].
        - initial_balance (float): Initial balance for the portfolio.
        """
        self.data = data
        self.initial_balance = initial_balance
        self.transaction_fee = transaction_fee

        # Agent uses actions [1, 0, -1] so they have to be translated
        self.action_mapping = {
            1: PositionType.LONG,
            0: PositionType.HOLD,
            -1: PositionType.SHORT
        }

        # (agent action, type of open position) -> function
        # functions open_new_position, buy_more, sell ore not pure as they update position and balance
        self.action_position_mapping = {
            ((PositionType.LONG, PositionType.HOLD), (PositionType.SHORT, PositionType.HOLD)): self.open_new_position,
            ((PositionType.LONG, PositionType.LONG), (PositionType.SHORT, PositionType.SHORT)): self.buy_more,
            ((PositionType.LONG, PositionType.SHORT), (PositionType.SHORT, PositionType.LONG)): self.sell,
            ((PositionType.HOLD, PositionType.HOLD), (PositionType.HOLD, PositionType.LONG), (PositionType.HOLD, PositionType.SHORT)): self.hold,
        }

        self.reset()

    def reset(self):
        """
        Reset the trading environment to its initial state.
        """
        self.current_step = 0
        self.balance = self.initial_balance
        self.current_state = self.data.iloc[self.current_step, :].values

        self.portfolio_value = 0
        self.position = {'position_type': PositionType.HOLD,
                         'owned_volume': 0,
                         'purchase_price': 0}

    def step(self, action, volume):
        """
        Perform a trading step based on the given action and volume.

        Parameters:
        - action (PositionType): Action to perform (LONG, HOLD, SHORT).
        - volume (float): Volume of shares to transact.

        This method updates the trading environment based on the agent's action.
        """
        # Convert action to PositionType
        action = self.action_mapping.get(action)
        # TODO: Volume can not be 0
        # Update current state and portfolio value
        self.current_state = self.data.iloc[self.current_step, :].values
        # open price from the current state
        current_price = self.current_state[1]
        self.portfolio_value = self.update_portfolio_value(current_price)

        # Get the function to perform based on action performed by agent and the current position type
        action_position = (action, self.position['position_type'])
        outcome_function = self.get_action_position_outcome(action_position)

        # Update position and balance
        outcome_function(action=action,
                         volume=volume,
                         current_price=current_price)

        # Update portfolio value again
        self.portfolio_value = self.update_portfolio_value(current_price)

        # Do the step
        self.current_step += 1

    def get_action_position_outcome(self, action_position):
        """
        Get the corresponding outcome function for the given action and position type.

        Parameters:
        - action_position (tuple): Tuple representing (action, position type).

        Returns:
        - function: Corresponding outcome function.
        """
        for keys, function in self.action_position_mapping.items():
            if action_position in keys:
                return function

    def open_new_position(self, action, volume, current_price):
        """
        Open a new position in the trading environment.

        Parameters:
        - action (PositionType): Action to perform (LONG, SHORT).
        - volume (float): Volume of shares to transact.
        - current_price (float): Current share price.

        This function has side effects:
        - It updates the balance and position of the trading environment.
        """
        # Calculate the total cost of transaction and based on that update the balance
        cost = volume * current_price
        self.balance -= cost
        # TODO: Check if you can afford it
        # Open a new position
        self.position = {'position_type': action,
                         'owned_volume': volume,
                         'purchase_price': current_price}
        # Pay transaction fee
        self.pay_transaction_fee()
        print(
            f"New transaction \nType: {action} | Volume: {volume} | Price: {current_price} | Cost: {cost}")
        print(f"New position opened. {self.position}")

    def buy_more(self, action, volume, current_price):
        """
        Buy more shares for an existing position.

        Parameters:
        - action (PositionType): Action to perform (LONG, SHORT).
        - volume (float): Volume of shares to transact.
        - current_price (float): Current share price.

        This function has side effects:
        - It updates the balance and position of the trading environment.
        """
        position_type, owned_volume, purchase_price = self.position.values()
        # Calculate the total cost of transaction and based on that update the balance
        cost = volume * current_price
        self.balance -= cost
        # TODO: Check if you can afford it
        # Calculate new volume and purchase price and update position
        new_volume = owned_volume + volume
        new_purchase_price = np.average(
            a=[purchase_price, current_price], weights=[owned_volume, volume])
        self.position = {'position_type': position_type,
                         'owned_volume': new_volume,
                         'purchase_price': new_purchase_price}
        # Pay transaction fee
        self.pay_transaction_fee()
        print(
            f"New transaction \nType: {action} | Volume: {volume} | Price: {current_price} | Cost: {cost}")
        print(f"Position updated. {self.position}")

    def sell(self, action, volume, current_price):
        """
        Sell shares in the trading environment.

        Parameters:
        - action (PositionType): Action to perform (LONG, SHORT).
        - volume (float): Volume of shares to transact.
        - current_price (float): Current share price.

        This function has side effects:
        - It updates the balance and position of the trading environment.
        """
        position_type, owned_volume, purchase_price = self.position.values()
        # Sell some
        if owned_volume > volume:
            # Alternative method for calculating outcome (Share of volume to sell in total volume)
            # sell_to_owned_ratio = volume/owned_volume
            # outcome = sell_to_owned_ratio * self.portfolio_value
            # outcome = self.portfolio_value * volume / owned_volume
            profit_per_share = (self.portfolio_value -
                                purchase_price * owned_volume)/owned_volume
            total_profit = profit_per_share * volume
            outcome = (purchase_price + profit_per_share) * volume
            # Print status
            print(
                f'Selling {volume} of Position Type: {position_type} for {current_price}. Transaction profit: {total_profit}')
            # Update the balance
            self.balance += outcome
            # Calculate how much volume has left
            remaining_volume = owned_volume - volume
            # Update position (position type and purchase price stays the same)
            self.position = {'position_type': position_type,
                             'owned_volume': remaining_volume,
                             'purchase_price': purchase_price}
        # Sell all
        elif owned_volume <= volume:
            # Calculate total transaction profit
            total_profit = self.portfolio_value - owned_volume * purchase_price
            # Update the balance
            self.balance += self.portfolio_value
            # Print status
            print(
                f'Selling {volume} of Position Type {position_type} for {current_price}. Transaction profit: {total_profit}')
            print(f'Position closed')
            # Zero the position
            self.position = {'position_type': PositionType.HOLD,
                             'owned_volume': 0,
                             'purchase_price': 0}
            # Open reverse if there is some remaining volume
            if (remaining_volume := volume - owned_volume) > 0:
                self.open_new_position(action=action,
                                       volume=remaining_volume,
                                       current_price=current_price)
        # Pay transaction fee
        self.pay_transaction_fee()

    def hold(self, action, volume, current_price):
        print('Hold')
        pass

    def pay_transaction_fee(self):
        """
        Pay the transaction fee.

        This function has side effects:
        - It updates the balance by substracting fee from it.
        """
        self.balance -= self.transaction_fee
        print(f'Transaction fee has been paid. Amount: {self.transaction_fee}')

    def update_portfolio_value(self, current_price):
        """
        Update the portfolio value based on the current position.

        Parameters:
        - current_price (float): Current share price.

        Returns:
        - float: Updated portfolio value.
        """
        position_type, owned_volume, purchase_price = self.position.values()
        if position_type == PositionType.LONG:
            # Earn when current_price goes up
            # new_portfolio_value = (purchase_price * owned_volume) + (current_price - purchase_price) * owned_volume
            new_portfolio_value = current_price * owned_volume
        elif position_type == PositionType.SHORT:
            # Earn when price current_price goes down
            # new_portfolio_value = (purchase_price * owned_volume) + (purchase_price - current_price) * owned_volume
            new_portfolio_value = 2 * purchase_price * \
                owned_volume - current_price * owned_volume
        else:  # position_type == PositionType.HOLD - there is no open position
            new_portfolio_value = 0
        return new_portfolio_value

    def print_status(self):
        print(f'Current state: {self.current_state}')
        print(f'Open position: {self.position}')
        print(f'Balance: {self.balance}')
        print(f'Portfolio value: {self.portfolio_value}')
