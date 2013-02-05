Thanks for your order!

% if echeck:
    Because you paid by e-check, it will take several days for your payment to clear.
    Once it does, our system will automatically send you an email with information on
    how to activate your purchase.
% else:
    % if new:
        Your New License ID is: ${regid}

        To activate your new license, (blah blah blah)
    % else:
        Upgrade for License ID: ${regid}

        To upgrade your license, (blah blah blah)
    % endif
% endif

Products Purchased:
% for item in order.items:
        ${item.product.name}
% endfor

Order #${order.order_id}, Total: $${'%.2f'%order.total}
