import numpy as np


class TradingEnvironment:
    def __init__(self, data, initial_balance):
        """
        Parameters:
        - data (pandas.DataFrame): Historical price data [Timestamp, Open, High, Low, Close, Volume].
        - initial_balance (float): Initial balance for the portfolio.
        """
        self.data = data  # data
        self.max_steps = len(self.data)  # max number of steps
        self.initial_balance = initial_balance

        self.reset()

    def reset(self):
        self.current_step = 0
        self.current_balance = self.initial_balance
        self.current_state = self.data.iloc[self.current_step, :].values

        self.portfolio_value = 0
        self.position = [0, 0, 0]  # (Direction, Share, Price)

    def step(self, action, share):
        """
        Perform an action of the Agent in the Environment.
        Available actions: [-1 - Sell, 0 - Hold, 1 - Buy]
        Share: size of the share you want the Agent to purchase.
        """
        self.current_step += 1
        self.current_state = self.data.iloc[self.current_step, :].values

        reward = 0

        # If there is no open position
        if self.position[0] == 0:
            # Neither buy nor sell
            if action == 0:
                print('There are no open positions.')
            # Buy/Sell depending on provided action
            else:
                # Assign new position
                self.position, added_portfolio_value = self.open_new_position(
                    action=action, share=share)
                # Reduce current balance
                self.current_balance -= added_portfolio_value
                # Increase portfolio value
                self.portfolio_value += added_portfolio_value
                print(f'New position opened: {self.position}')

        # If Long position is open
        elif self.position[0] == 1:
            # Hold
            if action == 0:
                print(f'You hold: {self.position}')
            # Buy more Long
            elif action == 1:
                # Update current position
                self.position, added_portfolio_value = self.buy_more(
                    share=share)
                # Reduce current balance
                self.current_balance -= added_portfolio_value
                # Increase portfolio value
                self.portfolio_value += added_portfolio_value
                print(f'Position updated: {self.position}')
            # Sell Long (and open Short)
            elif action == -1:
                owned_share = self.position[1]
                # Just sell
                purchase_price = self.position[2]
                current_price = self.current_state[1]
                # Positive - earned, negative - lost
                price_diff = current_price - purchase_price

                # Sell less or equal to what you own
                if share <= owned_share:
                    outcome = price_diff * share
                    # Update current balance
                    self.current_balance += outcome
                    # Update portfolio value
                    self.portfolio_value -= outcome
                    if share == owned_share:
                        # Reset position
                        self.position = (0, 0, 0)
                        print(f'Share sold: {self.position}')
                    else:
                        # Update owned share
                        self.position[1] -= share
                        print(f'Position updated: {self.position}')
                # Sell more than you own
                else:
                    outcome = price_diff * owned_share
                    # Update current balance
                    self.current_balance += outcome
                    # Update portfolio value
                    self.portfolio_value -= outcome
                    # Calculate remaining share and open position based on that
                    remaining_share = share - owned_share
                    self.position, added_portfolio_value = self.open_new_position(
                        action=action, share=remaining_share)
                    # Reduce current balance
                    self.current_balance -= added_portfolio_value
                    # Increase portfolio value
                    self.portfolio_value += added_portfolio_value
                    print(f'New position opened: {self.position}')

                print(f'Transaction outcome: {outcome}')

        # If Short position is open
        elif self.position[0] == -1:
            # Hold
            if action == 0:
                print(f'You hold: {self.position}')
            # Buy more Short
            elif action == -1:
                # Update current position
                self.position, added_portfolio_value = self.buy_more(
                    share=share)
                # Reduce current balance
                self.current_balance -= added_portfolio_value
                # Increase portfolio value
                self.portfolio_value += added_portfolio_value
                print(f'Position updated: {self.position}')
            # Sell Short (and buy Long)
            elif action == 1:
                owned_share = self.position[1]
                # Just sell
                purchase_price = self.position[2]
                current_price = self.current_state[1]
                # Positive - earned, negative - lost
                price_diff = current_price - purchase_price

                # Sell less or equal to what you own
                if share <= owned_share:
                    outcome = -price_diff * share
                    # Update current balance
                    self.current_balance += outcome
                    # Update portfolio value
                    self.portfolio_value -= outcome
                    if share == owned_share:
                        # Reset position
                        self.position = (0, 0, 0)
                        print(f'Share sold: {self.position}')
                    else:
                        # Update owned share
                        self.position[1] -= share
                        print(f'Position updated: {self.position}')
                # Sell more than you own
                else:
                    outcome = -price_diff * owned_share
                    # Update current balance
                    self.current_balance += outcome
                    # Update portfolio value
                    self.portfolio_value -= outcome
                    # Calculate remaining share and open position based on that
                    remaining_share = share - owned_share
                    self.position, added_portfolio_value = self.open_new_position(
                        action=action, share=remaining_share)
                    # Reduce current balance
                    self.current_balance -= added_portfolio_value
                    # Increase portfolio value
                    self.portfolio_value += added_portfolio_value
                    print(f'New position opened: {self.position}')

                print(f'Transaction outcome: {outcome}')

        # TODO: Portfolio value should update after every step
        current_price = self.current_state[1]
        owned_share = self.position[1]
        self.portfolio_value = current_price * owned_share
        return reward

    def calculate_reward(self):
        pass

    def open_new_position(self, action, share):
        # Get the current price and value
        price = self.current_state[1]
        # Calculate added portfolio value
        added_portfolio_value = price * share
        # "Open" the position
        position = [action, share, price]

        return position, added_portfolio_value

    def buy_more(self, share):
        price = self.current_state[1]
        added_portfolio_value = price * share
        final_position = [self.position[0],
                          self.position[1] + share,
                          np.average(a=[self.position[2], price],
                                     weights=[self.position[1], share])]

        return final_position, added_portfolio_value

    def print_status(self):
        print(f'Step: {self.current_step}')
        print(f'State: {self.current_state}')
        print(f'Current balance: {self.current_balance}')
        print(f'Portfolio value: {self.portfolio_value}')
