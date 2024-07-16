from datetime import datetime
import json
import httpx
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="API Performance Tester", page_icon="📊", layout="wide")

N_REQUESTS_UNSUCCESFUL_THRESHOLD = 5
UNSUCCESFUL_THRESHOLD = 0.5

client = httpx.Client()


def result_generator(url, request, *, count: int):
    for i in range(count):
        start = datetime.now()
        response = client.send(request)
        status_code = response.status_code
        result = {
            "start": start,
            "end": start + response.elapsed,
            "body": response.text if hasattr(response, "text") else None,
            "status_code": status_code,
            "response_time": response.elapsed.total_seconds(),
            "is_error": status_code != 200,
        }
        yield result


def draw_response_time_chart(df: pd.DataFrame) -> alt.Chart:
    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "start:T",
                axis=alt.Axis(format="%H:%M:%S", tickCount="second", grid=True),
            ),
            y="response_time:Q",
            # color=alt.Color('is_error:N', scale=alt.Scale(domain=[True, False], range=['darkorange', 'steelblue']))
        )
        .properties(title="Response time over time")
    )
    return chart


def draw_response_time_histogram(df: pd.DataFrame) -> alt.Chart:
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("response_time:Q", bin=True),
            y="count()",
        )
        .properties(title="Response time distribution")
    )
    return chart


def main():
    st.title("Performance results")

    # Sidebar containing all user inputs
    with st.sidebar:
        st.header("Settings")
        url = st.text_input("Request URL")
        count = st.number_input(
            "Number of requests", min_value=1, max_value=1000, value=10
        )
        if count:
            count = int(count)
        request_method = st.selectbox("Request type", ["GET", "POST"]) or "GET"
        request_headers = st.text_input(label="Request headers (json)", type="password")
        if request_headers:
            try:
                request_headers = json.loads(request_headers)
            except Exception as e:
                st.write(f"Could not parse headers as json: {e}")
        request_body = None
        if request_method == "POST":
            text_or_file = st.radio("Request body", ["Text", "File"], index=0)
            if text_or_file == "File":
                uploaded_file = st.file_uploader("Choose a file")
                if uploaded_file:
                    request_body = uploaded_file.read()
            elif text_or_file == "Text":
                request_body = st.text_area(
                    "Request body",
                    height=100,
                )

        if request_body:
            try:
                request_body = json.loads(request_body)
            except Exception as e:
                st.write(f"Could not parse body as json: {e}")

        start_button = st.button("Start")

    error_rate = 0
    total_time = 0
    average_response_time = 0

    if start_button:
        results = []
        result_df = pd.DataFrame()

        col1, col2, col3, col4 = st.columns(4)
        total_request_metric = col1.empty()
        requests_per_second_metric = col2.empty()
        avg_response_time_metric = col3.empty()
        error_rate_metric = col4.empty()
        st.divider()

        col1, col2 = st.columns(2)

        response_time_chart = col1.empty()
        response_time_histogram = col2.empty()

        request = client.build_request(
            method=request_method,
            url=url,
            json=request_body,
            timeout=30,
            headers={"Content-Type": "application/json", **request_headers},
        )
        for i, result in enumerate(
            iterable=result_generator(url, request, count=count)
        ):
            results.append(result)
            result_df = pd.DataFrame(results)

            # Calculate and update metrics
            error_rate = 1 - (
                result_df["status_code"].value_counts().get(200, 0) / len(result_df)
            )

            if (
                i > N_REQUESTS_UNSUCCESFUL_THRESHOLD
                and error_rate > UNSUCCESFUL_THRESHOLD
            ):
                st.error(
                    f"Error: More than {UNSUCCESFUL_THRESHOLD:.0%} of requests are failing, stopping the test"
                )
                break

            total_time = (
                result_df["end"].max() - result_df["start"].min()
            ).total_seconds()
            average_response_time = result_df["response_time"].mean()

            total_request_metric = total_request_metric.metric(
                label="Total requests sent", value=len(result_df)
            )
            requests_per_second_metric.metric(
                label="Requests/s",
                value=f"{(len(result_df) / total_time):.2f} requests/s",
            )
            avg_response_time_metric.metric(
                label="Avg. Response Time (seconds)",
                value=f"{average_response_time:.3f} seconds",
            )
            error_rate_metric.metric(
                label="Error rate", value=f"{(error_rate*100):.2f}%"
            )

            # Update the charts
            line_chart = draw_response_time_chart(result_df)
            response_time_chart = response_time_chart.altair_chart(
                line_chart,
                use_container_width=True,
            )
            hist_chart = draw_response_time_histogram(result_df)
            response_time_histogram = response_time_histogram.altair_chart(
                hist_chart,
                use_container_width=True,
            )

        #     col1, col2 = st.columns(2)
        #     with col1:
        #         respone_time_chart = draw_chart()

        #         st.altair_chart(chart, use_container_width=True)
        #     with col2:
        #         chart = alt.Chart(result_df).mark_bar().encode(
        #             x=alt.X("response_time:Q", bin=True),
        #             y='count()',
        #         )
        #         st.altair_chart(chart, use_container_width=True)
        st.divider()

        st.header("Detailed results")
        st.dataframe(result_df, hide_index=True)
    else:
        st.info("Please enter the URL and click start")


if __name__ == "__main__":
    main()
