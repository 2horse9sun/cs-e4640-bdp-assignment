/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.app;

import org.apache.flink.api.common.eventtime.Watermark;
import org.apache.flink.api.common.eventtime.WatermarkGenerator;
import org.apache.flink.api.common.eventtime.WatermarkGeneratorSupplier;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.common.serialization.SimpleStringEncoder;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.api.java.functions.KeySelector;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.api.java.tuple.Tuple3;
import org.apache.flink.configuration.MemorySize;
import org.apache.flink.connector.elasticsearch.sink.Elasticsearch7SinkBuilder;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.core.fs.Path;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.annotation.JsonPropertyOrder;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.DataStreamSource;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.AssignerWithPeriodicWatermarks;
import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.streaming.api.functions.sink.filesystem.rollingpolicies.DefaultRollingPolicy;
import org.apache.flink.streaming.api.functions.windowing.WindowFunction;
import org.apache.flink.streaming.api.windowing.assigners.SlidingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer;
import org.apache.flink.util.Collector;
import org.apache.flink.util.OutputTag;
import org.apache.http.HttpHost;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.action.update.UpdateRequest;
import org.elasticsearch.client.Requests;
import org.apache.flink.connector.file.sink.FileSink;

import java.time.Duration;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

/**
 * Skeleton for a Flink DataStream Job.
 *
 * <p>For a tutorial how to write a Flink application, check the
 * tutorials and examples on the <a href="https://flink.apache.org">Flink Website</a>.
 *
 * <p>To package your application into a JAR file for execution, run
 * 'mvn clean package' on the command line.
 *
 * <p>If you change the name of the main class (with the public static void main(String[] args))
 * method, change the respective entry in the POM.xml file (simply search for 'mainClass').
 */
public class DataStreamJob {


	public static class SensorEvent {
		public Long sensorTimestamp;
		public Tuple2<String, String> sensorLocation;
		public String countryCode;
		public Double P1;
		public Double P2;

		public SensorEvent() {}

		public SensorEvent(Long sensorTimestamp, Tuple2<String, String> sensorLocation, String countryCode,
						   Double P1, Double P2) {
			this.sensorTimestamp = sensorTimestamp;
			this.sensorLocation = sensorLocation;
			this.countryCode = countryCode;
			this.P1 = P1;
			this.P2 = P2;
		}

		@Override
		public String toString() {
			return "SensorEvent{" +
					"sensorTimestamp=" + sensorTimestamp +
					", sensorLocation=" + sensorLocation +
					", countryCode=" + countryCode +
					", P1=" + P1 +
					", P2=" + P2 +
					'}';
		}
	}

	public static class AvgGeoAirQualityStats {
		public Long sensorTimestamp;
		public Tuple2<String, String> sensorLocation;
		public String countryCode;
		public Double avgP1;
		public Double avgP2;

		public AvgGeoAirQualityStats() {}

		public AvgGeoAirQualityStats(Long sensorTimestamp, Tuple2<String, String> sensorLocation, String countryCode,
						   Double avgP1, Double avgP2) {
			this.sensorTimestamp = sensorTimestamp;
			this.sensorLocation = sensorLocation;
			this.countryCode = countryCode;
			this.avgP1 = avgP1;
			this.avgP2 = avgP2;
		}

		@Override
		public String toString() {
			return sensorTimestamp +
					"," + sensorLocation.f0 +
					"," + sensorLocation.f1 +
					"," + countryCode +
					"," + avgP1 +
					"," + avgP2;
		}
	}


	public static void main(String[] args) throws Exception {

		final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

//		env.setParallelism(4);

		DataStreamSource<String> csvStream = env.fromSource(
				KafkaSource.<String>builder()
				.setBootstrapServers("kafka01:9092")
				.setTopics("air")
				.setGroupId("air-group")
				.setStartingOffsets(OffsetsInitializer.earliest())
				.setValueOnlyDeserializer(new SimpleStringSchema())
				.build(),
				WatermarkStrategy.noWatermarks(),
				"Kafka Source");

		final OutputTag<Tuple2<Long, String>> errorTag = new OutputTag<Tuple2<Long, String>>("error-output"){};

		SingleOutputStreamOperator<SensorEvent> sensorEventStream =
				csvStream
				.process(new ProcessFunction<String, SensorEvent>() {
					@Override
					public void processElement(String line, Context context, Collector<SensorEvent> collector) throws Exception {
						// Parse the CSV row and assign names to each field
						try {
							String[] fields = line.split(",");
							DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
							Long sensorTimestamp = LocalDateTime.parse(fields[0], formatter).toEpochSecond(ZoneOffset.UTC) * 1000L;
							Tuple2<String, String> sensorLocation = Tuple2.of(fields[1], fields[2]);
							String countryCode = fields[3];
							Double P1 = Double.parseDouble(fields[4]);
							Double P2 = Double.parseDouble(fields[5]);
							collector.collect(new SensorEvent(sensorTimestamp, sensorLocation, countryCode, P1, P2));
						}catch (Exception e){
							String[] fields = line.split(",");
							DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
							Long sensorTimestamp = LocalDateTime.parse(fields[0], formatter).toEpochSecond(ZoneOffset.UTC) * 1000L;
							context.output(errorTag, Tuple2.of(sensorTimestamp, line));
						}
					}
				});


		DataStream<Tuple2<Long, String>> invalidFormatStream = sensorEventStream.getSideOutput(errorTag);

		DataStream<AvgGeoAirQualityStats> avgGeoAirQualityStatsStream =
				sensorEventStream
				.assignTimestampsAndWatermarks(
						WatermarkStrategy
						.<SensorEvent>forBoundedOutOfOrderness(Duration.ofMinutes(1))
						.withTimestampAssigner(((sensorEvent, l) -> sensorEvent.sensorTimestamp))
						.withIdleness(Duration.ofSeconds(5))
				)
				.keyBy(new KeySelector<SensorEvent, Tuple2<String, String>>() {
					@Override 
					public Tuple2<String, String> getKey(SensorEvent event) throws Exception {
						return event.sensorLocation;
					}
				})
				.window(TumblingEventTimeWindows.of(Time.minutes(5)))
				.allowedLateness(Time.minutes(5))
				.apply(new AverageAggregateFunction());


		avgGeoAirQualityStatsStream.sinkTo(
				new Elasticsearch7SinkBuilder<AvgGeoAirQualityStats>()
						.setBulkFlushMaxActions(1) // Instructs the sink to emit after every element, otherwise they would be buffered
						.setHosts(new HttpHost("es01", 9200, "http"))
						.setEmitter(
								(element, context, indexer) ->
										indexer.add(createAvgGeoAirQualityStatsRequest(element)))
						.build());

//		avgGeoAirQualityStatsStream.print();

		invalidFormatStream.sinkTo(
				new Elasticsearch7SinkBuilder<Tuple2<Long, String>>()
						.setBulkFlushMaxActions(1) // Instructs the sink to emit after every element, otherwise they would be buffered
						.setHosts(new HttpHost("es01", 9200, "http"))
						.setEmitter(
								(element, context, indexer) ->
										indexer.add(createInvalidSensorDataRequest(element)))
						.build());


		env.execute("Average Air Quality Analytics Job");

	}

	private static IndexRequest createAvgGeoAirQualityStatsRequest(AvgGeoAirQualityStats avgGeoAirQualityStats) {
		Map<String, Object> json = new HashMap<>();
		json.put("sensorTimestamp", avgGeoAirQualityStats.sensorTimestamp);
		json.put("sensorLocation", String.join(",", avgGeoAirQualityStats.sensorLocation.f0, avgGeoAirQualityStats.sensorLocation.f1));
		json.put("countryCode", avgGeoAirQualityStats.countryCode);
		json.put("avgP1", avgGeoAirQualityStats.avgP1);
		json.put("avgP2", avgGeoAirQualityStats.avgP2);
		return Requests.indexRequest()
				.index("avg-geo-air-quality-stats")
				.source(json);
	}

	private static IndexRequest createInvalidSensorDataRequest(Tuple2<Long, String> error) {
		Map<String, Object> json = new HashMap<>();
		json.put("sensorTimestamp", error.f0);
		json.put("sensorData", error.f1);
		return Requests.indexRequest()
				.index("invalid-sensor-data")
				.source(json);
	}

	public static class AverageAggregateFunction implements WindowFunction<SensorEvent, AvgGeoAirQualityStats, Tuple2<String, String>, TimeWindow> {

		@Override
		public void apply(Tuple2<String, String> key, TimeWindow window, Iterable<SensorEvent> input, Collector<AvgGeoAirQualityStats> out) {
			Double sumP1 = 0D;
			Double sumP2 = 0D;
			Long count = 0L;
			Long maxTimestamp = 0L;
			String countryCode = "";

			// Accumulate the sum of P1 and P2 and the count of elements in the window
			for (SensorEvent event : input) {
				sumP1 += event.P1;
				sumP2 += event.P2;
				count++;
				maxTimestamp = Math.max(event.sensorTimestamp, maxTimestamp);
				countryCode = event.countryCode;
			}

			// Compute the average of P1 and P2 and emit the result with the sensorLocation key
			Double avgP1 = sumP1 / count;
			Double avgP2 = sumP2 / count;
			out.collect(new AvgGeoAirQualityStats(maxTimestamp, key, countryCode, sumP1, sumP2));
		}
	}


}
