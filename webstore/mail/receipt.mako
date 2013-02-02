Thanks for your order!


% if new:
    Your New License ID is: ${regid}

    To activate your new license, (blah blah blah)
% else:
    Upgrade for License ID: ${regid}

    To upgrade your license, (blah blah blah)
% endif

Products Purchased:
% for item in order.items:
        ${item.product.name}
% endfor

Order #${order.order_id}, Total: $${order.total}
