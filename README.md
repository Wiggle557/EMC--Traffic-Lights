# EMC--Traffic-Lights

We are currently using a max-pressure/dynamic green allocation scheme to actuate the green light. There is a set timing for the red light, but the green light is actuated based on the number of cars waiting at the intersection. The more cars waiting, the longer the green light stays on. This is a simple scheme that works well in most cases, but it can be improved by using a more sophisticated algorithm that takes into account the traffic flow and other factors. 
The current red light timing is set to 15 seconds and the intermediary colours are set at being 3 seconds each.
Coming into a junction there are 2 conflict groups, one for each direction. They comprise the horizontal and vertical traffic flows. The 'pressure' for each group is calculated by summing the number of cars in each of the roads.
Then each light within the 'winning group' is actuated for using the following formula:
```green_time = min(15 + (total_pressure * 2), 30)```
then the lights in the other group are set to red for the same amount of time.
