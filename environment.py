import numpy as np
from enum import Enum


class PositionType(Enum):
    LONG = 1
    HOLD = 0
    SHORT = -1


class TradingEnvironment:
    def __init__(self, data, initial_balance, transaction_fee):
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
        self.current_step = 0
        self.balance = self.initial_balance
        self.current_state = self.data.iloc[self.current_step, :].values

        self.portfolio_value = 0
        self.position = {'position_type': PositionType.HOLD,
                         'owned_volume': 0,
                         'purchase_price': 0}

    def step(self, action, volume):
        game_over = False
        # Convert action to PositionType
        self.action = self.action_mapping.get(action)

        # Volume can not be 0
        if ((volume == 0) and (self.action != PositionType.HOLD)):
            print('Error: Volume cannot be zero for LONG and SHORT.')  # TODO
            self.action = PositionType.HOLD
            return game_over, self.balance, self.action

        # Update current state and portfolio value
        self.current_state = self.data.iloc[self.current_step, :].values
        # open price from the current state
        current_price = self.current_state[1]
        self.portfolio_value = self.update_portfolio_value(current_price)

        # Stop loss check
        if self.stop_loss(current_price) == True:
            print('Game over: Stop loss triggered.')
            game_over = True
            self.portfolio_value = self.update_portfolio_value(current_price)
            return game_over, self.balance, self.action

        # Get the function to perform based on action performed by agent and the current position type
        action_position = (self.action, self.position['position_type'])
        outcome_function = self.get_action_position_outcome(action_position)

        # Update position and balance
        outcome_function(action=self.action,
                         volume=volume,
                         current_price=current_price)

        # Update portfolio value again
        self.portfolio_value = self.update_portfolio_value(current_price)

        # Do the step
        self.current_step += 1

        return game_over, self.balance, self.action

    def get_action_position_outcome(self, action_position):
        for keys, function in self.action_position_mapping.items():
            if action_position in keys:
                return function
        print('Error: Action position outcome not found.')

    def open_new_position(self, action, volume, current_price):
        # Check if you can afford this much volume and if not, reduce it
        cost, volume = self.cost_volume_calculator(volume, current_price)

        if cost == 0:
            # print('Error: Not enough funds to open position.') # TODO
            self.action = PositionType.HOLD
            return

        # Update the balance
        self.balance -= cost

        # Open a new position
        self.position = {'position_type': action,
                         'owned_volume': volume,
                         'purchase_price': current_price}
        # Pay transaction fee
        self.pay_transaction_fee()
        print(
            f"Opened new {action.name} position:\nVolume: {volume}\nPurchase Price: {current_price}\nCost: {cost}")

    def buy_more(self, action, volume, current_price):
        position_type, owned_volume, purchase_price = self.position.values()

        # Check if you can afford this much volume and if not, reduce it
        cost, volume = self.cost_volume_calculator(volume, current_price)

        if cost == 0:
            # print('Error: Not enough funds to buy more.') # TODO
            self.action = PositionType.HOLD
            return

        self.balance -= cost
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
            f"Bought more {action.name} position:\nAdditional Volume: {volume}\nUpdated Purchase Price: {new_purchase_price}\nCost: {cost}")

    def sell(self, action, volume, current_price):
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
                f'Sold {owned_volume} shares of {position_type.name} position for {current_price}.\nTotal Transaction Profit: {total_profit}')
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
                f'Sold {volume} shares of {position_type.name} position for {current_price}.\nTotal Transaction Profit: {total_profit}')
            print('Position closed')
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
        pass

    def pay_transaction_fee(self):
        self.balance -= self.transaction_fee

    def update_portfolio_value(self, current_price):
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

    def stop_loss(self, current_price):
        if (self.portfolio_value + self.balance <= 0) or (self.balance <= 0):
            print('Stop loss triggered. Selling position.')
            print(
                f'Portfolio value: {self.portfolio_value} | Balance: {self.balance}')
            # Sell everything
            position_type, owned_volume, purchase_price = self.position.values()
            opposite_action = PositionType.SHORT if position_type == PositionType.LONG else PositionType.LONG
            self.action = opposite_action
            self.sell(action=opposite_action,
                      volume=owned_volume,
                      current_price=current_price)
            return True
        else:
            return False

    def cost_volume_calculator(self, volume, current_price):
        # Check if you can buy all volume
        if self.balance >= volume * current_price + self.transaction_fee:
            return volume * current_price, volume
        # Buy as much as you can
        else:
            # print('Warning: Not enough funds to buy desired volume. Adjusting volume.') # TODO
            # TODO: Set the parameter for it
            new_volume = np.floor(
                ((self.balance - self.transaction_fee) / current_price))
            return new_volume * current_price, new_volume

    def print_status(self):
        print("Current Status:")
        print(f"  Current State: {self.current_state}")
        print(f"  Open Position: {self.position}")
        print(f"  Balance: {self.balance}")
        print(f"  Portfolio Value: {self.portfolio_value}")
        print()
